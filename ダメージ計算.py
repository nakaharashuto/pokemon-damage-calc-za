import streamlit as st
import math
import uuid
import pandas as pd

# --- 1. 共通定数 (省略) ---
ZA_CORRECTION_RATIO = 2868 / 4096 # ZA補正係数
IV_RANGES = {
    "さいこう/きたえた! (31)": (31, 31),
    "すばらしい (30)": (30, 30),
    "すごくいい (26-29)": (26, 29),
    "かなりいい (16-25)": (16, 25),
    "まあまあ (1-15)": (1, 15),
    "ダメかも (0)": (0, 0)
}
NATURE_MODIFIERS = {
    "補正なし (neutral)": 1.0,
    "補正あり (up)": 1.1,
    "下降補正 (down)": 0.9,
}
BATTLE_MODIFIERS = {
    "能力変化なし (1.0倍)": 1.0,
    "能力アップ (1.5倍)": 1.5,
}
TECHNIQUE_PLUS_MODIFIERS = {
    "通常 (1.0倍)": 1.0,
    "通常技プラス (1.2倍)": 1.2,
    "メガシンカ状態 (1.3倍)": 1.3,
}
STAB_CHOICES = {"タイプ一致 (1.5倍)": 1.5, "タイプ不一致 (1.0倍)": 1.0}
TYPE_EFFECTIVENESS_CHOICES = {
    "4倍弱点 (4.0倍)": 4.0, 
    "2倍弱点 (2.0倍)": 2.0, 
    "等倍 (1.0倍)": 1.0, 
    "半減 (0.5倍)": 0.5, 
    "1/4 (0.25倍)": 0.25, 
    "無効 (0.0倍)": 0.0
}
OTHER_ITEM_FIELD_MODIFIER_CHOICES = {
    "補正なし (1.0倍)": 1.0,
    "急所 (1.5倍)": 1.5,
    "こだわりハチマキ/メガネ (1.5倍)": 1.5,
    "いのちのたま (1.3倍)": 1.3,
    "達人の帯 (1.2倍)": 1.2,
    "その他 (任意)": 1.0, 
}
TECHNIQUE_CATEGORY_CHOICES = ["物理 (A vs B)", "特殊 (C vs D)"]
WALL_MODIFIER = 0.5

IV_CHOICES = list(IV_RANGES.keys())
NATURE_CHOICES = list(NATURE_MODIFIERS.keys())
BATTLE_CHOICES = list(BATTLE_MODIFIERS.keys())
TECHNIQUE_PLUS_CHOICES = list(TECHNIQUE_PLUS_MODIFIERS.keys())
TYPE_LIST = ["ノーマル", "ほのお", "みず", "でんき", "くさ", "こおり", "かくとう", "どく", "じめん", "ひこう", "エスパー", "むし", "いわ", "ゴースト", "ドラゴン", "はがね", "フェアリー", "あく"]
# 初期化時に更新されるため、ここでは空リストを設定
VIRTUAL_P_CHOICES = [] 

# --- 1.5 共通インデックス取得 (省略) ---
STAB_1_0_INDEX = list(STAB_CHOICES.keys()).index("タイプ不一致 (1.0倍)")
TYPE_1_0_INDEX = list(TYPE_EFFECTIVENESS_CHOICES.keys()).index("等倍 (1.0倍)")
OTHER_1_0_INDEX = list(OTHER_ITEM_FIELD_MODIFIER_CHOICES.keys()).index("補正なし (1.0倍)")


# --- 2. 共通計算関数 (変更なし) ---
def get_iv_range(choice):
    return IV_RANGES.get(choice, (31, 31))

def calculate_stat_value(base_stat, iv, ev, level, nature_modifier, battle_modifier):
    """攻撃/防御/特攻/特防/素早さの実数値を計算し、戦闘補正を適用する"""
    if base_stat == 0: return 0
    ev_contribution = ev // 4
    calc_base = math.floor((base_stat * 2 + iv + ev_contribution) * level / 100) + 5
    stat_after_nature = math.floor(calc_base * nature_modifier)
    final_stat = math.floor(stat_after_nature * battle_modifier)
    return final_stat

def calculate_hp_value(base_hp, iv, ev, level):
    """HPの実数値を計算する"""
    if base_hp == 1:
        return 1
    ev_contribution = ev // 4
    calc_base = math.floor((base_hp * 2 + iv + ev_contribution) * level / 100) + level + 10
    return calc_base

def calculate_damage_base(level, power, attack, defense, correction_ratio_no_rng_with_tech_plus, is_za=False):
    """ダメージを計算する。is_za=TrueならZA補正をかける。"""
    
    base_calc_1 = math.floor(level * 2 / 5) + 2
    base_calc_2 = math.floor(base_calc_1 * power * attack / defense)
    base_damage = math.floor(base_calc_2 / 50) + 2
    final_damage_max = math.floor(base_damage * correction_ratio_no_rng_with_tech_plus)
    
    # ZA補正のみを適用 (is_zaがTrueの場合)
    if is_za:
        final_damage_max = math.floor(final_damage_max * ZA_CORRECTION_RATIO)
    
    return final_damage_max

def calculate_ttk(min_dmg, max_dmg, hp):
    """TTK (Time To Knockout) を計算する"""
    if hp <= 0 or min_dmg <= 0: return "N/A"
    
    max_hits = math.ceil(hp / min_dmg)
    min_hits = math.ceil(hp / max_dmg)
    
    if min_dmg >= hp:
        return "確定1発"
    elif max_hits == min_hits:
        return f"確定{max_hits}発"
    else:
        return f"乱数{min_hits}〜{max_hits}発"

def perform_damage_calc(level, power, attack, defense, def_hp, final_correction_ratio):
    """ダメージ計算を行い、ZAのダメージ幅とTTKを返す (SV結果は除外)"""
    
    # ZAの結果のみを取得
    za_result_max = calculate_damage_base(level, power, attack, defense, final_correction_ratio, is_za=True)
    
    za_min_damage = math.floor(za_result_max * 0.85)
    
    za_dmg_range = f"{za_min_damage}～{za_result_max}"
    
    za_ttk = calculate_ttk(za_min_damage, za_result_max, def_hp)
    
    return za_dmg_range, za_ttk # ZAの結果のみを返す

# --- 3. セッションステート初期化と管理関数 (変更なし) ---

def initialize_session_state():
    if 'my_pokemons' not in st.session_state:
        # 初期データとして例をいくつか追加 (HABCDS種族値と個体値のみ)
        st.session_state['my_pokemons'] = [
            {'id': str(uuid.uuid4()), 'name': 'アタッカーA', 'level': 50, 
             'H_base': 100, 'A_base': 130, 'B_base': 80, 'C_base': 80, 'D_base': 80, 'S_base': 100,
             'H_iv': 'さいこう/きたえた! (31)', 'A_iv': 'さいこう/きたえた! (31)', 'B_iv': 'さいこう/きたえた! (31)', 
             'C_iv': 'さいこう/きたえた! (31)', 'D_iv': 'さいこう/きたえた! (31)', 'S_iv': 'さいこう/きたえた! (31)',
             'att_stat_name': '攻撃', 'def_stat_name': '防御'}, # 旧データ保持のため残すが、シミュレーションで上書き
            {'id': str(uuid.uuid4()), 'name': '受けポケモンB', 'level': 50, 
             'H_base': 95, 'A_base': 100, 'B_base': 100, 'C_base': 100, 'D_base': 120, 'S_base': 60,
             'H_iv': 'さいこう/きたえた! (31)', 'A_iv': 'さいこう/きたえた! (31)', 'B_iv': 'さいこう/きたえた! (31)', 
             'C_iv': 'さいこう/きたえた! (31)', 'D_iv': 'さいこう/きたえた! (31)', 'S_iv': 'さいこう/きたえた! (31)',
             'att_stat_name': '特攻', 'def_stat_name': '特防'}
        ]
    
    # 仮想敵選択肢を最新に更新
    st.session_state['VIRTUAL_P_CHOICES'] = ["直接実数値入力"] + ["マイポケモン: " + p['name'] for p in st.session_state.get('my_pokemons', [])]


def display_pokemon_list():
    """登録済みポケモンリストをサイドバーに表示する (表示は種族値/個体値のみ)"""
    st.sidebar.markdown("### 登録済みポケモンリスト (マイポケモン)")
    if not st.session_state.my_pokemons:
        st.sidebar.caption("ポケモンが登録されていません。")
        return
        
    for i, p in enumerate(st.session_state.my_pokemons):
        if st.sidebar.button("削除", key=f"delete_btn_{p['id']}"):
            st.session_state.my_pokemons.pop(i)
            st.experimental_rerun()
            return
            
        with st.sidebar.expander(f"No.{i+1} : **{p['name']}**"):
            level = p.get('level', 50)
            st.caption(f"Lv: {level}")
            
            st.caption("--- 種族値/個体値 ---")
            stats = ['H', 'A', 'B', 'C', 'D', 'S']
            stat_info = [f"{s} B:{p[f'{s}_base']} I:{p[f'{s}_iv'][:5]}" for s in stats]
            st.caption(", ".join(stat_info))

# --- 4. ポケモン登録フォーム関数 (変更なし) ---
def register_pokemon_form():
    st.markdown("---")
    st.subheader("📝 新規ポケモン登録 (種族値・個体値のみ)")
    
    with st.form("register_pokemon"):
        p_name = st.text_input("ポケモンの名前 (ニックネーム)", key="reg_name", value="新規ポケモン")
        p_level = st.number_input("レベル", min_value=1, max_value=100, value=50, step=1, key="reg_level")
        
        stat_inputs = {}
        iv_inputs = {}
        
        stat_names = ['H', 'A', 'B', 'C', 'D', 'S']
        
        for s in stat_names:
            st.markdown(f"##### {s} 設定")
            col_base, col_iv = st.columns(2)
            with col_base: 
                stat_inputs[f'{s}_base'] = st.number_input(f"{s} 種族値", min_value=1, value=100, key=f"reg_{s}_base")
            with col_iv: 
                iv_inputs[f'{s}_iv'] = st.selectbox(f"{s} 個体値", options=IV_CHOICES, key=f"reg_{s}_iv")

        submitted = st.form_submit_button("このポケモンを登録")
        
        if submitted:
            new_pokemon = {
                'id': str(uuid.uuid4()),
                'name': p_name,
                'level': p_level,
                **stat_inputs,
                **iv_inputs,
                'att_stat_name': '攻撃', 'def_stat_name': '防御' # ダミーとして残すがシミュレーションで上書き
            }
            st.session_state.my_pokemons.append(new_pokemon)
            st.session_state['VIRTUAL_P_CHOICES'] = ["直接実数値入力"] + ["マイポケモン: " + p['name'] for p in st.session_state.get('my_pokemons', [])]
            st.success(f"{p_name} を登録しました！")
            st.experimental_rerun()

# --- 5. ダメージ計算結果表示関数 (詳細モード専用の新しい関数を修正) ---
def calculate_and_print_st_detailed(level, power, 
                                    a_base, a_ev, a_nature, a_battle_mod, a_iv_choice,
                                    d_base, d_ev, d_nature, d_battle_mod, d_iv_choice,
                                    d_hp_base, d_hp_ev, d_hp_iv_choice,
                                    final_correction_ratio):
    """詳細モードの結果を計算し、Streamlitに出力する"""
    
    # 1. IVのブレ幅を取得
    a_iv_min, a_iv_max = get_iv_range(a_iv_choice)
    d_iv_min, d_iv_max = get_iv_range(d_iv_choice)
    d_hp_iv_min, d_hp_iv_max = get_iv_range(d_hp_iv_choice)

    # 2. 実数値のブレ幅を計算
    
    # 攻撃側 実数値ブレ幅
    att_min_value = calculate_stat_value(a_base, a_iv_min, a_ev, level, a_nature, a_battle_mod)
    att_max_value = calculate_stat_value(a_base, a_iv_max, a_ev, level, a_nature, a_battle_mod)
    att_value_range_str = f"{att_min_value}～{att_max_value}"
    
    # 防御側 実数値ブレ幅
    def_min_value = calculate_stat_value(d_base, d_iv_min, d_ev, level, d_nature, d_battle_mod)
    def_max_value = calculate_stat_value(d_base, d_iv_max, d_ev, level, d_nature, d_battle_mod)
    def_value_range_str = f"{def_min_value}～{def_max_value}"


    # 3. ダメージ最大値の計算に必要な実数値 (攻MAX vs 防MIN)
    # ※防御側の実数値が低いほどダメージは最大になる
    attack_for_max_dmg = att_max_value
    defense_for_max_dmg = def_min_value
    
    # ダメージ最大値を算出
    # (ダメージの乱数最大 + 個体値/実数値のブレによる最大値)
    za_result_max = calculate_damage_base(level, power, attack_for_max_dmg, defense_for_max_dmg, final_correction_ratio, is_za=True)

    # 4. ダメージ最小値の計算に必要な実数値 (攻MIN vs 防MAX)
    # ※防御側の実数値が高いほどダメージは最小になる
    attack_for_min_dmg = att_min_value
    defense_for_min_dmg = def_max_value
    
    # ダメージ最小値を算出 (乱数最小 0.85倍 + 個体値/実数値のブレによる最小値)
    za_result_min_raw = calculate_damage_base(level, power, attack_for_min_dmg, defense_for_min_dmg, final_correction_ratio, is_za=True)
    za_min_damage = math.floor(za_result_min_raw * 0.85)

    # 5. TTK計算用のHP実数値 (HPは最大値を使用し、最も耐久がある状態を想定)
    def_hp_value = calculate_hp_value(d_hp_base, d_hp_iv_max, d_hp_ev, level)
    
    # 6. 結果の整形
    za_dmg_range = f"{za_min_damage}～{za_result_max}"
    za_ttk = calculate_ttk(za_min_damage, za_result_max, def_hp_value)
    
    # ★★★ 変更点: 実数値のブレ幅を表示 ★★★
    st.markdown(f"**--- 計算結果 (ダメージブレ幅は設定された個体値幅を考慮) ---**")
    st.markdown(f"**参照実数値**: 攻撃: **{att_value_range_str}** / 防御: **{def_value_range_str}**")
    
    st.info(f"🚀 **ZA (仮説) ダメージ幅**: **{za_dmg_range}** ダメージ")
    
    st.markdown(f"**--- TTK (防御側HP: {def_hp_value} (IV MAX)) ---**")
    
    st.write(f"  **ZA TTK**: {za_ttk}")
    st.caption(f"（TTKは設定HPの最大実数値 ({d_hp_iv_max}) に対して計算）")
    # ★★★ 変更点: ここまで ★★★

# --- 6. 各計算モード関数 (変更なし) ---

# 詳細モード (種族値/EV入力) - 変更なし (calculate_and_print_st_detailedのみ変更)
def run_detailed_mode_st_functional():
    st.subheader("詳細モード: 種族値/EV入力")
    
    with st.form("easy_calc_form"):
        # 1. 共通設定 (省略)
        level = st.number_input("ポケモンのレベル", min_value=1, max_value=100, value=50, step=1, key="easy_level")
        
        st.markdown("---")

        # 2. ⚔️ 攻撃側の設定
        st.markdown("#### ⚔️ 攻撃側の設定")
        col_a_base, col_a_ev, col_a_n, col_a_bm = st.columns(4)
        with col_a_base: a_base = st.number_input("攻撃/特攻 種族値", min_value=1, value=120, key="easy_a_base")
        with col_a_ev: a_ev = st.number_input("努力値 (0～252)", min_value=0, max_value=252, value=252, step=4, key="easy_a_ev")
        with col_a_n: 
            a_nature_choice = st.selectbox("性格補正", options=NATURE_CHOICES, index=0, key="easy_a_n")
        with col_a_bm: 
            a_battle_choice = st.selectbox("戦闘中補正", options=BATTLE_CHOICES, index=0, key="easy_a_bm")
            
        a_iv_choice = st.selectbox("個体値", options=IV_CHOICES, key="easy_a_iv")
        
        st.markdown("---")

        # 3. ⚙️ 技と補正の設定 (省略)
        st.markdown("#### ⚙️ 技と補正の設定 (攻撃側が持つ補正)")
        power = st.number_input("技の威力", min_value=1, value=100, step=1, key="easy_power")
        
        st.caption("💥 ZA独自の補正（技プラス）")
        tech_plus_choice = st.selectbox("技プラス補正", options=TECHNIQUE_PLUS_MODIFIERS, index=0, key="easy_tech")
        tech_plus_mod = TECHNIQUE_PLUS_MODIFIERS[tech_plus_choice]
        
        st.markdown("###### 乱数・技プラス以外の補正設定")
        col_stab, col_type, col_item = st.columns(3)
        with col_stab:
            stab_choice = st.selectbox("STAB (タイプ一致)", options=list(STAB_CHOICES.keys()), index=STAB_1_0_INDEX, key="easy_stab")
            stab_mod = STAB_CHOICES[stab_choice]
        with col_type:
            type_choice = st.selectbox("タイプ相性 (弱点/半減)", options=list(TYPE_EFFECTIVENESS_CHOICES.keys()), index=TYPE_1_0_INDEX, key="easy_type")
            type_mod = TYPE_EFFECTIVENESS_CHOICES[type_choice]
        with col_item:
            other_choice = st.selectbox("道具・フィールド補正", options=list(OTHER_ITEM_FIELD_MODIFIER_CHOICES.keys()), index=OTHER_1_0_INDEX, key="easy_other")
            other_mod = OTHER_ITEM_FIELD_MODIFIER_CHOICES[other_choice]

        if other_choice == "その他 (任意)":
            other_mod = st.number_input("任意補正倍率", min_value=0.0, value=1.0, step=0.1, key="easy_other_custom")

        st.markdown("---")

        # 4. 🛡️ 防御側の設定
        st.markdown("#### 🛡️ 防御側の設定")
        col_d_base, col_d_ev, col_d_n, col_d_bm = st.columns(4)
        with col_d_base: d_base = st.number_input("防御/特防 種族値", min_value=1, value=100, key="easy_d_base")
        with col_d_ev: d_ev = st.number_input("防御/特防 努力値 (0～252)", min_value=0, max_value=252, value=252, step=4, key="easy_d_ev")
        with col_d_n: 
            d_nature_choice = st.selectbox("防御/特防 性格補正", options=NATURE_CHOICES, index=0, key="easy_d_n")
        with col_d_bm: 
            d_battle_choice = st.selectbox("防御/特防 戦闘中補正", options=BATTLE_CHOICES, index=0, key="easy_d_bm")
            
        d_iv_choice = st.selectbox("防御/特防 個体値", options=IV_CHOICES, key="easy_d_iv")
        
        st.markdown("HP設定")
        col_hp_base, col_hp_ev = st.columns(2)
        with col_hp_base: d_hp_base = st.number_input("HP 種族値", min_value=1, value=90, key="easy_d_hp_base")
        with col_hp_ev: d_hp_ev = st.number_input("HP 努力値 (0～252)", min_value=0, max_value=252, value=252, step=4, key="easy_d_hp_ev")
        d_hp_iv_choice = st.selectbox("HP 個体値", options=IV_CHOICES, key="easy_d_hp_iv")
        
        st.markdown("---")

        # 5. 壁（リフレクター/ひかりのかべ）補正 (省略)
        st.markdown(f"#### 🛡️ 壁（リフレクター/ひかりのかべ）補正 (補正: {WALL_MODIFIER}倍) (防御側が持つ補正)")
        
        wall_mod = 1.0
        wall_mod_select = st.radio("【適用倍率】壁の適用方法", ["壁なし (1.0)", "壁あり (0.5)"], horizontal=True, index=0, key="easy_wall_apply_simple")
        
        if "0.5" in wall_mod_select:
             wall_mod = WALL_MODIFIER

        # 総補正の計算 (省略)
        a_nature_mod = NATURE_MODIFIERS[a_nature_choice]
        a_battle_mod = BATTLE_MODIFIERS[a_battle_choice]
        d_nature_mod = NATURE_MODIFIERS[d_nature_choice]
        d_battle_mod = BATTLE_MODIFIERS[d_battle_choice]
        
        base_correction_ratio = stab_mod * type_mod * other_mod * wall_mod
        final_correction_ratio = base_correction_ratio * tech_plus_mod
        
        st.caption(f"**最終補正倍率**: {final_correction_ratio:.3f}")
        
        st.markdown("---")


        calc_submitted = st.form_submit_button("計算を実行")

        if calc_submitted:
            st.subheader("計算結果：ダメージレンジ")
            
            # 詳細モードの計算関数を呼び出す
            calculate_and_print_st_detailed(
                level, power, 
                a_base, a_ev, a_nature_mod, a_battle_mod, a_iv_choice,
                d_base, d_ev, d_nature_mod, d_battle_mod, d_iv_choice,
                d_hp_base, d_hp_ev, d_hp_iv_choice,
                final_correction_ratio
            )
            
# 簡単モード (実数値入力) - 変更なし
def run_easy_mode_st_functional():
    # 既存の簡単モードのコードをそのまま維持
    def calculate_and_print_st(level, power, attack, defense, def_hp, final_correction_ratio, stat_type):
        """計算を実行し、ZAの結果を整形してStreamlitに出力する (SV結果は除外)"""
        
        # ZAの結果のみを取得
        za_dmg_range, za_ttk = perform_damage_calc(level, power, attack, defense, def_hp, final_correction_ratio)
        
        st.markdown(f"**--- 計算結果 (実数値: 攻 {attack} / 防 {defense}) ---**")
        
        st.info(f"🚀 **ZA (仮説) ダメージ幅**: **{za_dmg_range}** ダメージ")

        st.markdown(f"**--- TTK (防御側HP: {def_hp}) ---**")
        
        st.write(f"  **ZA TTK**: {za_ttk}")

    st.subheader("簡単モード: 実数値で入力")
    
    with st.form("detailed_calc_form"):
        # 1. 共通設定 (省略)
        st.markdown("#### 共通設定")
        level = st.number_input("ポケモンのレベル", min_value=1, max_value=100, value=50, step=1, key="det_level")
        
        st.markdown("---")

        # 2. ⚔️ 攻撃側の実数値と補正 (省略)
        st.markdown("#### ⚔️ 攻撃側の実数値と補正")
        col_att_val, col_att_bm = st.columns(2) # カラムを追加
        with col_att_val:
            attack_value = st.number_input("攻撃実数値 (A or C)", min_value=1, value=150, step=1, key="det_att_value")
        with col_att_bm:
            att_battle_choice = st.selectbox("戦闘中能力変化", options=BATTLE_CHOICES, index=0, key="det_att_bm")
            att_battle_mod = BATTLE_MODIFIERS[att_battle_choice]
            
        st.markdown("---")

        # 3. ⚙️ 技と補正の設定 (省略)
        st.markdown("#### ⚙️ 技と補正の設定 (攻撃側が持つ補正)")
        power = st.number_input("技の威力", min_value=1, value=100, step=1, key="det_power")
        
        st.caption("💥 ZA独自の補正（技プラス）")
        tech_plus_choice = st.selectbox("技プラス補正", options=TECHNIQUE_PLUS_MODIFIERS, index=0, key="det_tech")
        tech_plus_mod = TECHNIQUE_PLUS_MODIFIERS[tech_plus_choice]
        
        st.markdown("###### 乱数・技プラス以外の補正設定")
        col_stab, col_type, col_item = st.columns(3)
        with col_stab:
            stab_choice = st.selectbox("STAB (タイプ一致)", options=list(STAB_CHOICES.keys()), index=STAB_1_0_INDEX, key="det_stab")
            stab_mod = STAB_CHOICES[stab_choice]
        with col_type:
            type_choice = st.selectbox("タイプ相性 (弱点/半減)", options=list(TYPE_EFFECTIVENESS_CHOICES.keys()), index=TYPE_1_0_INDEX, key="det_type")
            type_mod = TYPE_EFFECTIVENESS_CHOICES[type_choice]
        with col_item:
            other_choice = st.selectbox("道具・フィールド補正", options=list(OTHER_ITEM_FIELD_MODIFIER_CHOICES.keys()), index=OTHER_1_0_INDEX, key="det_other")
            other_mod = OTHER_ITEM_FIELD_MODIFIER_CHOICES[other_choice]

        if other_choice == "その他 (任意)":
            other_mod = st.number_input("任意補正倍率", min_value=0.0, value=1.0, step=0.1, key="det_other_custom")
        
        st.markdown("---")

        # 4. 🛡️ 防御側の実数値と補正 (省略)
        st.markdown("#### 🛡️ 防御側の実数値と補正")
        col_def_val, col_def_bm = st.columns(2) # カラムを追加
        with col_def_val:
            defense_value = st.number_input("防御実数値 (B or D)", min_value=1, value=130, step=1, key="det_def_value")
        with col_def_bm:
            def_battle_choice = st.selectbox("戦闘中能力変化", options=BATTLE_CHOICES, index=0, key="det_def_bm")
            def_battle_mod = BATTLE_MODIFIERS[def_battle_choice]

        hp_def = st.number_input("防御側HP実数値", min_value=1, value=200, step=1, key="det_hp_def")
        
        st.markdown("---")

        # 5. 壁（リフレクター/ひかりのかべ）補正 (省略)
        st.markdown(f"#### 🛡️ 壁（リフレクター/ひかりのかべ）補正 (補正: {WALL_MODIFIER}倍) (防御側が持つ補正)")
        
        wall_mod = 1.0
        wall_mod_select = st.radio("【適用倍率】壁の適用方法", ["壁なし (1.0)", "壁あり (0.5)"], horizontal=True, index=0, key="det_wall_apply_simple")
        
        if "0.5" in wall_mod_select:
             wall_mod = WALL_MODIFIER


        # 総補正の計算 (省略)
        base_correction_ratio = stab_mod * type_mod * other_mod * wall_mod
        final_correction_ratio = base_correction_ratio * tech_plus_mod
        
        st.caption(f"**乱数・技プラス以外の総補正**: {base_correction_ratio:.3f}")
        st.caption(f"**最終補正倍率**: {final_correction_ratio:.3f}")
        
        st.markdown("---")

        calc_submitted = st.form_submit_button("計算を実行")

        if calc_submitted:
            st.subheader("計算結果：ダメージレンジ")
            
            # 攻撃値に戦闘中補正を適用
            final_attack_value = math.floor(attack_value * att_battle_mod) 
            
            # 防御値に戦闘中補正を適用
            final_defense_value = math.floor(defense_value * def_battle_mod)
            
            # 単一の実数値で計算を実行
            calculate_and_print_st(level, power, final_attack_value, final_defense_value, hp_def, final_correction_ratio, 
                                  f"設定値 (攻:{final_attack_value} / 防:{final_defense_value})")


# 関数名と機能の対応を維持
run_detailed_mode_st = run_detailed_mode_st_functional # 詳細モード（種族値/EV入力）
run_easy_mode_st = run_easy_mode_st_functional # 簡単モード（実数値入力）


# --- 7. マイポケモン vs 仮想敵シミュレーションモード (変更なし) ---
def get_stats_from_settings(p_data, ev_dict, nature_dict, battle_mod_dict, level):
    """登録情報とシミュレーション入力から全実数値 (MAX/MIN) を計算して返す"""
    stats_result = {}
    
    # 性格補正を辞書に変換
    nature_mods = {stat: 1.0 for stat in ['H', 'A', 'B', 'C', 'D', 'S']}
    for stat, nature_choice in nature_dict.items():
        nature_mods[stat] = NATURE_MODIFIERS[nature_choice]
    
    for stat in ['H', 'A', 'B', 'C', 'D', 'S']:
        base = p_data[f'{stat}_base']
        ev = ev_dict.get(stat, 0)
        iv_choice = p_data[f'{stat}_iv']
        # MAX/MINの両方を計算するために、IVレンジは残す
        iv_min, iv_max = get_iv_range(iv_choice)
        
        # 性格補正の適用 (H/Sには適用しない)
        nature_mod = nature_mods[stat] if stat in ['A', 'B', 'C', 'D'] else 1.0
        
        # 戦闘中能力変化補正の適用
        battle_mod = battle_mod_dict.get(stat, 1.0)
        
        if stat == 'H':
            # HPの計算 (戦闘中能力変化補正は適用しない)
            stats_result[f'{stat}_max'] = calculate_hp_value(base, iv_max, ev, level)
            stats_result[f'{stat}_min'] = calculate_hp_value(base, iv_min, ev, level)
        else:
            # 他の能力値の計算
            stats_result[f'{stat}_max'] = calculate_stat_value(base, iv_max, ev, level, nature_mod, battle_mod)
            stats_result[f'{stat}_min'] = calculate_stat_value(base, iv_min, ev, level, nature_mod, battle_mod)
            
    return stats_result


def get_virtual_pokemon_stats(choice, my_poke_list, target_stat_name, hp_stat_name=None):
    """直接実数値入力モードで使用する、仮想敵の素の種族値/個体値からの実数値計算（旧形式の互換用）"""
    if choice == "直接実数値入力":
        return None, None, None, None, None, None
    
    # マイポケモンのデータを取得
    poke_name = choice.replace("マイポケモン: ", "")
    p = next(p for p in my_poke_list if p['name'] == poke_name)
    level = p['level']
    
    # 新しい登録形式から対応する種族値と個体値を取得
    stat_map = {'攻撃': 'A', '特攻': 'C', '防御': 'B', '特防': 'D'}
    stat_key = stat_map.get(target_stat_name, 'A')

    # EV/性格補正は不明なので、ここでは簡易的にEV0, 性格補正1.0, 戦闘補正1.0, 個体値MAXとして計算 (直接入力時の目安として使用)
    base = p[f'{stat_key}_base']
    iv_choice = p[f'{stat_key}_iv']
    iv_min, iv_max = get_iv_range(iv_choice)
    
    # 簡易計算 (EV 0, 性格 1.0, 戦闘 1.0)
    stat_max = calculate_stat_value(base, iv_max, 0, level, 1.0, 1.0)
    stat_min = calculate_stat_value(base, iv_min, 0, level, 1.0, 1.0) # 参照元としては使われないが計算しておく

    hp_max = None
    hp_min = None
    if hp_stat_name == 'H':
        hp_iv_min, hp_iv_max = get_iv_range(p['H_iv'])
        hp_max = calculate_hp_value(p['H_base'], hp_iv_max, 0, level)
        hp_min = calculate_hp_value(p['H_base'], hp_iv_min, 0, level)

    # 仮想敵の場合、防御能力は戦闘補正(def_battle_mod)の適用が必要だが、ここでは素の値を返し、シミュレーションパートで適用する
    return stat_max, stat_min, hp_max, hp_min, p, level


def run_battle_sim_mode_st():
    st.subheader("⚔️ マイポケモン vs 仮想敵シミュレーション")
    
    if not st.session_state.my_pokemons:
        st.warning("先に「マイポケモン管理」セクションでポケモンを登録してください。")
        return

    pokemon_names = [p['name'] for p in st.session_state.my_pokemons]
    
    # ------------------------------------
    # 1. 役割選択とポケモン選択
    # ------------------------------------
    st.markdown("### 1. 役割とマイポケモン選択")
    sim_mode = st.radio(
        "シミュレーションの役割を選択",
        ["⚔️ 自分のポケモン (1体) が攻撃側", "🛡️ 自分のポケモン (1体) が防御側"],
        horizontal=True,
        key="sim_mode_select"
    )

    is_att_vs_def = (sim_mode == "⚔️ 自分のポケモン (1体) が攻撃側")
    
    if is_att_vs_def:
        my_role_name = "攻撃側 (マイポケモン)"
        att_name = st.selectbox(my_role_name, options=pokemon_names, key="sim_my_att")
        my_poke = next(p for p in st.session_state.my_pokemons if p['name'] == att_name)
    else:
        my_role_name = "防御側 (マイポケモン)"
        def_name = st.selectbox(my_role_name, options=pokemon_names, key="sim_my_def")
        my_poke = next(p for p in st.session_state.my_pokemons if p['name'] == def_name)

    st.caption(f"選択ポケモン: **{my_poke['name']}** (Lv:{my_poke['level']})")
    st.markdown("---")
    
    # ------------------------------------
    # 2. マイポケモンの詳細設定 (EV, 性格補正, 能力変化)
    # ------------------------------------
    st.markdown("### 2. マイポケモンの詳細設定 (EV・性格・戦闘中補正)")
    
    # 努力値 (EV) 入力
    st.markdown("##### 努力値 (EV) 設定")
    ev_inputs = {}
    stats = ['H', 'A', 'B', 'C', 'D', 'S']
    cols = st.columns(6)
    for i, stat in enumerate(stats):
        # 初期値を全て 0 に設定済み
        default_ev = 0 
        with cols[i]:
            ev_inputs[stat] = st.number_input(f"{stat} EV", min_value=0, max_value=252, value=default_ev, step=4, key=f"sim_ev_{stat}")

    # 性格補正入力
    st.markdown("##### 性格補正設定")
    nature_inputs = {}
    nature_stats = ['A', 'B', 'C', 'D']
    nature_cols = st.columns(4)
    for i, stat in enumerate(nature_stats):
        with nature_cols[i]:
            # デフォルトを「補正なし (neutral)」(1.0倍) に設定
            nature_inputs[stat] = st.selectbox(f"{stat} 性格補正", options=NATURE_CHOICES, index=0, key=f"sim_nature_{stat}")
            
    # 戦闘中能力変化補正入力
    st.markdown("##### 戦闘中能力変化補正")
    battle_mod_inputs = {}
    battle_stats = ['A', 'B', 'C', 'D']
    battle_cols = st.columns(4)
    for i, stat in enumerate(battle_stats):
        with battle_cols[i]:
            # 攻撃側ならA/C、防御側ならB/Dにのみ変更UIを表示
            if (is_att_vs_def and stat in ['A', 'C']) or (not is_att_vs_def and stat in ['B', 'D']):
                # デフォルトを「能力変化なし (1.0倍)」に設定
                battle_mod_inputs[stat] = st.selectbox(f"{stat} 能力変化", options=BATTLE_CHOICES, index=0, key=f"sim_bm_{stat}")
            else:
                battle_mod_inputs[stat] = BATTLE_CHOICES[0] # デフォルト値 "能力変化なし (1.0倍)"
            
    # 全実数値計算 (MAX/MIN)
    my_stats = get_stats_from_settings(
        my_poke, ev_inputs, nature_inputs, 
        {stat: BATTLE_MODIFIERS[battle_mod_inputs[stat]] for stat in battle_mod_inputs}, 
        my_poke['level']
    )
    
    st.caption(f"実数値 (MAX/MIN): H:{my_stats['H_max']}/{my_stats['H_min']}, A:{my_stats['A_max']}/{my_stats['A_min']}, C:{my_stats['C_max']}/{my_stats['C_min']}, B:{my_stats['B_max']}/{my_stats['B_min']}, D:{my_stats['D_max']}/{my_stats['D_min']}")
    st.markdown("---")
    
    # ------------------------------------
    # 3. 技と共通補正の設定
    # ------------------------------------
    st.markdown("### 3. 技の分類と共通補正の設定")
    
    # 技の分類選択 (新要素)
    tech_category = st.radio("技の分類を選択", options=TECHNIQUE_CATEGORY_CHOICES, horizontal=True, index=0, key="sim_tech_category")
    is_physical = ("物理" in tech_category)
    
    # 技分類に基づく能力の決定
    att_stat_key = 'A' if is_physical else 'C'
    def_stat_key = 'B' if is_physical else 'D'
    att_stat_name = '攻撃' if is_physical else '特攻'
    def_stat_name = '防御' if is_physical else '特防'
    
    st.caption(f"**参照能力**: 攻: {att_stat_name} ({att_stat_key}) vs 防: {def_stat_name} ({def_stat_key})")
    
    # 共通技設定 (パワー、STAB, 技プラス, アイテム/フィールド)
    col_power, col_stab, col_tech = st.columns(3)
    with col_power: power = st.number_input("技の威力", min_value=1, value=100, step=1, key="sim_power")
    with col_stab: 
        # デフォルトを「タイプ不一致 (1.0倍)」に設定
        stab_choice = st.selectbox("STAB (タイプ一致)", options=list(STAB_CHOICES.keys()), index=STAB_1_0_INDEX, key="sim_stab")
        att_stab_mod = STAB_CHOICES[stab_choice]
    with col_tech: 
        # デフォルトを「通常 (1.0倍)」に設定
        tech_plus_choice = st.selectbox("ZA独自の補正（技プラス）", options=TECHNIQUE_PLUS_MODIFIERS, index=0, key="sim_tech_plus")
        att_tech_plus_mod = TECHNIQUE_PLUS_MODIFIERS[tech_plus_choice]

    col_item, col_wall = st.columns(2)
    with col_item: 
        # デフォルトを「補正なし (1.0倍)」に設定
        other_choice = st.selectbox("道具・フィールド補正", options=list(OTHER_ITEM_FIELD_MODIFIER_CHOICES.keys()), index=OTHER_1_0_INDEX, key="sim_other")
        att_other_mod = OTHER_ITEM_FIELD_MODIFIER_CHOICES[other_choice]
        if other_choice == "その他 (任意)":
            att_other_mod = st.number_input("任意補正倍率", min_value=0.0, value=1.0, step=0.1, key="sim_other_custom")

    # 壁設定
    with col_wall:
        st.markdown(f"##### 壁 (防御側補正: {WALL_MODIFIER}倍)")
        wall_mod = 1.0
        # デフォルトを「壁なし (1.0)」に設定
        wall_mod_select = st.radio("壁の適用方法", ["壁なし (1.0)", "壁あり (0.5)"], horizontal=True, index=0, key="sim_wall_apply_simple")
        if "0.5" in wall_mod_select:
             wall_mod = WALL_MODIFIER

    # 攻撃側が持つ基本補正の計算 (相性・壁以外)
    att_base_mod = att_stab_mod * att_other_mod * att_tech_plus_mod
    st.markdown("---")
    
    # ------------------------------------
    # 4. 仮想敵 3体の設定 (防御側は個別にタイプ相性)
    # ------------------------------------
    st.subheader("### 4. 📊 仮想敵 3体/攻撃技の設定") 

    enemy_stats = []
    
    for i in range(1, 4):
        st.markdown(f"##### 仮想敵 {i}")
        
        virtual_choice = st.selectbox(
            "能力値の参照元", 
            options=st.session_state.get('VIRTUAL_P_CHOICES', ["直接実数値入力"]), 
            key=f"enemy_{i}_choice"
        )
        
        # 仮想敵のデフォルト値設定（直接入力の目安またはマイポケモンからの参照）
        enemy_hp = 200
        enemy_stat_val = 150
        enemy_power = power # 攻撃側が自分なら共通技威力
        
        enemy_p = None
        if "マイポケモン:" in virtual_choice:
            # 仮想敵の種族値/個体値からEV0, 性格1.0, 戦闘1.0の値を参照
            stat_max, _, hp_max, _, enemy_p, _ = get_virtual_pokemon_stats(
                virtual_choice, st.session_state.my_pokemons, def_stat_name if is_att_vs_def else att_stat_name, 'H'
            )
            if enemy_p:
                enemy_stat_val = stat_max if stat_max is not None else 150
                enemy_hp = hp_max if hp_max is not None else 200
                st.caption(f"参照ポケモン: **{enemy_p['name']}** (EV0/性格補正なしのMAX実数値を使用)")

        col_name, col_stat_val, col_type_mod, col_power_i = st.columns(4)
        
        # 名前入力
        with col_name: name = st.text_input("名前", value=f"敵{i}" if is_att_vs_def else f"アタッカー{i}", key=f"enemy_{i}_name")
        
        # 実数値入力/参照
        with col_stat_val:
            if is_att_vs_def:
                # 攻撃側が自分: 仮想敵は防御側
                if virtual_choice == "直接実数値入力":
                    stat_val = st.number_input(f"{def_stat_name}実数値", min_value=1, value=enemy_stat_val, step=1, key=f"enemy_{i}_def_val")
                    enemy_hp = st.number_input("HP実数値", min_value=1, value=enemy_hp, step=1, key=f"enemy_{i}_hp_val")
                else:
                    st.text_input(f"{def_stat_name}実数値 (参照/目安)", value=enemy_stat_val, disabled=True, key=f"enemy_{i}_def_disp")
                    st.text_input("HP実数値 (参照/目安)", value=enemy_hp, disabled=True, key=f"enemy_{i}_hp_disp")
                enemy_power = power # 攻撃側が自分なので共通威力
            else:
                # 防御側が自分: 仮想敵は攻撃側
                if virtual_choice == "直接実数値入力":
                    stat_val = st.number_input(f"{att_stat_name}実数値", min_value=1, value=enemy_stat_val, step=1, key=f"enemy_{i}_att_val")
                else:
                    st.text_input(f"{att_stat_name}実数値 (参照/目安)", value=enemy_stat_val, disabled=True, key=f"enemy_{i}_att_disp")
                
                # 防御側が自分の場合、HPは自分のポケモンから取得
                stat_val = stat_val if virtual_choice == "直接実数値入力" else enemy_stat_val
        
        # 攻撃側が相手の場合、技威力とアイテム補正を個別に設定
        if not is_att_vs_def:
            with col_power_i:
                enemy_power = st.number_input("技の威力", min_value=1, value=enemy_power, step=1, key=f"enemy_{i}_power")
            
            st.caption("--- 仮想アタッカーの個別補正 ---")
            col_e_stab, col_e_item, col_e_tech = st.columns(3)
            with col_e_stab: 
                # デフォルトを「タイプ不一致 (1.0倍)」に設定
                stab_choice_e = st.selectbox("STAB", options=list(STAB_CHOICES.keys()), index=STAB_1_0_INDEX, key=f"enemy_{i}_stab")
                stab_mod_e = STAB_CHOICES[stab_choice_e]
            with col_e_item: 
                # デフォルトを「補正なし (1.0倍)」に設定
                other_choice_e = st.selectbox("道具補正", options=list(OTHER_ITEM_FIELD_MODIFIER_CHOICES.keys()), index=OTHER_1_0_INDEX, key=f"enemy_{i}_other")
                other_mod_e = OTHER_ITEM_FIELD_MODIFIER_CHOICES[other_choice_e]
            with col_e_tech: 
                # デフォルトを「通常 (1.0倍)」に設定
                tech_plus_choice_e = st.selectbox("ZA補正", options=TECHNIQUE_PLUS_MODIFIERS, index=0, key=f"enemy_{i}_tech_plus")
                tech_plus_mod_e = TECHNIQUE_PLUS_MODIFIERS[tech_plus_choice_e]
            
            att_base_mod = stab_mod_e * other_mod_e * tech_plus_mod_e # 仮想アタッカーが持つ補正
            
        with col_type_mod: 
            # デフォルトを「等倍 (1.0倍)」に設定
            type_mod_i = st.selectbox("タイプ相性", options=list(TYPE_EFFECTIVENESS_CHOICES.keys()), index=TYPE_1_0_INDEX, key=f"enemy_{i}_type")
            type_mod_val = TYPE_EFFECTIVENESS_CHOICES[type_mod_i]

        # 最終補正 = (攻撃側が持つ基本補正 * 相性 * 壁)
        final_correction_ratio = att_base_mod * type_mod_val * wall_mod
        
        enemy_stats.append({
            'name': name, 
            'hp': enemy_hp, 
            'stat': stat_val, # 仮想敵の実数値
            'power': enemy_power,
            'type_mod_name': type_mod_i,
            'final_ratio': final_correction_ratio,
            'is_att': not is_att_vs_def
        })
        
    st.markdown("---")
    
    # ------------------------------------
    # 5. 計算実行ボタンと結果表示
    # ------------------------------------
    if st.button("一括ダメージ計算を実行", key="run_sim_calc"):
        st.subheader("🎉 比較結果")
        results = []
        
        # 参照する実数値を決定
        if is_att_vs_def:
            # 自分の攻撃側能力値 (MAX/MIN)
            att_max = my_stats[f'{att_stat_key}_max']
            att_min = my_stats[f'{att_stat_key}_min']
        else:
            # 自分の防御側能力値 (MAX/MIN) とHP (MAX/MIN)
            def_max = my_stats[f'{def_stat_key}_max']
            def_min = my_stats[f'{def_stat_key}_min']
            def_hp_max = my_stats['H_max']
            def_hp_min = my_stats['H_min']
        
        for i, enemy in enumerate(enemy_stats):
            final_correction_ratio = enemy['final_ratio']
            power_i = enemy['power']
            level = my_poke['level']
            
            if is_att_vs_def:
                # 1体攻撃 vs 3体防御
                
                # 攻MAX vs 防御 (仮想敵) 実数値 (HPも仮想敵)
                za_range_max, za_ttk_max = perform_damage_calc(
                    level, power_i, att_max, enemy['stat'], enemy['hp'], final_correction_ratio
                )
                # 攻MIN vs 防御 (仮想敵) 実数値 (HPも仮想敵)
                za_range_min, za_ttk_min = perform_damage_calc(
                    level, power_i, att_min, enemy['stat'], enemy['hp'], final_correction_ratio
                )
                
                results.append({
                    '敵ポケモン': enemy['name'],
                    '技威力': power_i,
                    'HP実数値': enemy['hp'],
                    f'{def_stat_name}実数値': enemy['stat'],
                    'タイプ相性': enemy['type_mod_name'],
                    f'ZAダメ幅 (攻{att_stat_key} MAX)': za_range_max, 
                    f'ZA TTK (攻{att_stat_key} MAX)': za_ttk_max,     
                    f'ZAダメ幅 (攻{att_stat_key} MIN)': za_range_min, 
                    f'ZA TTK (攻{att_stat_key} MIN)': za_ttk_min,     
                })

            else:
                # 3体攻撃 vs 1体防御
                
                # 攻撃 (仮想敵) 実数値 vs 防御 MIN (TTK計算はHP MAXを使用)
                za_range_min, za_ttk_min = perform_damage_calc(
                    level, power_i, enemy['stat'], def_min, def_hp_max, final_correction_ratio
                )
                # 攻撃 (仮想敵) 実数値 vs 防御 MAX (TTK計算はHP MINを使用)
                za_range_max, za_ttk_max = perform_damage_calc(
                    level, power_i, enemy['stat'], def_max, def_hp_min, final_correction_ratio
                )
                
                results.append({
                    '攻撃側': enemy['name'],
                    '技威力': power_i,
                    f'{att_stat_name}実数値': enemy['stat'],
                    'タイプ相性': enemy['type_mod_name'],
                    f'ZAダメ幅 (防{def_stat_key} MIN / HP MAX)': za_range_min, 
                    f'ZA TTK (防{def_stat_key} MIN / HP MAX)': za_ttk_min,     
                    f'ZAダメ幅 (防{def_stat_key} MAX / HP MIN)': za_range_max, 
                    f'ZA TTK (防{def_stat_key} MAX / HP MIN)': za_ttk_max,     
                })
                
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True)


# --- 8. メイン実行関数 (変更なし) ---
def main_st():
    st.set_page_config(page_title="ポケモンダメージ計算機 (ZA補正対応)", layout="wide")
    st.title("🛡️⚔️ ポケモンダメージ計算機 (ZA仮説補正)")
    st.caption(f"ZA補正係数: {ZA_CORRECTION_RATIO:.6f} (2868/4096) - ※SVダメージは非表示")
    
    # セッションステートの初期化とリスト表示
    initialize_session_state()
    
    # サイドバーに登録済みポケモンリストを表示 (どのモードでも表示)
    display_pokemon_list()
    
    # メインのモード選択 (順番: 簡単、詳細、シミュレーション)
    selected_mode = st.radio("計算モードを選択", 
                            ["簡単モード", "詳細モード", "対戦シミュレーションモード"], 
                            horizontal=True, key="main_mode_select") 
    
    # 選択された名前に応じて、元の関数を呼び出す
    if selected_mode == "簡単モード":
        run_easy_mode_st() # 実数値入力
    elif selected_mode == "詳細モード":
        run_detailed_mode_st() # 種族値/EV入力
    elif selected_mode == "対戦シミュレーションモード":
        run_battle_sim_mode_st()
    
    # ポケモン登録フォーム
    st.markdown("---")
    st.header("マイポケモン管理")
    register_pokemon_form()
    
    st.markdown("""
    ---
    ### 補足情報
    * **表示される結果について**: 「詳細モード」では、**設定した個体値の最小値から最大値までのブレを全て考慮したダメージ幅**を、単一の結果として表示しています。また、参照した攻撃/防御の実数値ブレ幅を併記しました。
    * **TTK (Time To Knockout)**: ダメージ乱数最小/最大に基づき、敵HPを倒すのに必要な最小発数〜最大発数を示します。TTK計算には、防御側の設定個体値の**最大値**で計算されたHPを使用します。
    * **ZA補正係数**: 現在判明しているレイドボス補正（2868/4096）を暫定的に採用しています。
    """)

if __name__ == '__main__':
    main_st()