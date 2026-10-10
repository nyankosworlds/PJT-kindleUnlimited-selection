import json
import urllib.parse
import streamlit as st
from google import genai

# ---------------------------------------------------------
# 1. ページ初期設定
# ---------------------------------------------------------
st.set_page_config(
    page_title="Kindle選書AI",
    page_icon="📚",
    layout="centered"
)

# AmazonアソシエイトID（ご自身のアソシエイトIDを取得後に書き換えてください）
ASSOCIATE_TAG = "your_tracking_id-22"

# ---------------------------------------------------------
# 2. セッション状態（メモリ）の初期化
# ---------------------------------------------------------
if "history_titles" not in st.session_state:
    st.session_state.history_titles = []  # 提案済みタイトルの除外リスト
if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = [] # 現在表示中の結果

# ---------------------------------------------------------
# 3. UI表示（ヘッダー・入力フォーム）
# ---------------------------------------------------------
st.title("📚 あなたのためのAI選書")
st.caption("今の気分や読書履歴に合わせて、おすすめの本を5冊提案します。")

# 入力フォーム
user_input = st.text_area(
    "今の気分、興味のあるジャンル、最近読んだ本などを自由に入力してください",
    placeholder="例：仕事の合間にスマホでサクッと読めて癒やされるエッセイが読みたい。最近は刺し子をしながら流し読みできるような本が好き。",
    height=100
)

# モード選択
target_mode = st.radio(
    "対象エリア",
    ["Kindle Unlimited対象のみ", "Amazon全体"],
    horizontal=True
)

# ---------------------------------------------------------
# 4. 確実にヒットするAmazon検索リンク生成関数
# ---------------------------------------------------------
def create_amazon_url(search_keyword, mode):
    encoded_keyword = urllib.parse.quote(search_keyword)
    if mode == "Kindle Unlimited対象のみ":
        # Kindle Unlimited対象に絞り込む検索URLパラメータ
        url = (
            f"https://www.amazon.co.jp/s?k={encoded_keyword}"
            f"&i=digital-text"
            f"&rh=p_n_feature_nineteen_browse-bin%3A3169286051"
            f"&tag={ASSOCIATE_TAG}"
        )
    else:
        url = f"https://www.amazon.co.jp/s?k={encoded_keyword}&tag={ASSOCIATE_TAG}"
    return url

# ---------------------------------------------------------
# 5. AI選書ロジック（安定稼働版）
# ---------------------------------------------------------
def fetch_recommendations(prompt_text, exclude_list, mode):
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)

    system_instruction = """
    あなたは親切で優秀なプロの選書家です。
    ユーザーの入力内容に基づいて、Amazonで確実に見つけられる実在の書籍を5冊選定してください。
    Amazonの検索窓で一発でヒットするように、各書籍の「正確な書籍タイトルと著者名」を組み合わせた検索キーワードを必ず `search_keyword` に設定してください。
    
    必ず以下のJSON配列フォーマット「のみ」を出力してください。Markdownのコードブロック（```json ... ```）や前後の解説文は含めないでください。

    [
      {
        "title": "書籍タイトル",
        "author": "著者名",
        "reason": "おすすめの理由（100文字程度）",
        "search_keyword": "Amazon検索用キーワード（例: 書籍タイトル 著者名）"
      }
    ]
    """

    user_prompt = f"""
    【ユーザーのリクエスト】
    {prompt_text}

    【絞り込みモード】
    {mode}

    【除外リスト（以下のタイトルの本は絶対に選ばないでください）】
    {", ".join(exclude_list) if exclude_list else "なし"}
    """

    # ツールを使わず、純粋な生成とJSONモードで安定動作させる
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=user_prompt,
        config={
            "system_instruction": system_instruction,
            "response_mime_type": "application/json"
        }
    )

    try:
        raw_text = response.text.strip()
        # 万が一バッククォートが含まれていたら削る
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        data = json.loads(raw_text.strip())
        return data
    except Exception as e:
        st.error("AIからのデータ取得に失敗しました。もう一度お試しください。")
        return []

# ---------------------------------------------------------
# 6. ボタン処理とメイン描画
# ---------------------------------------------------------
col1, col2 = st.columns(2)

# 新規検索ボタン
with col1:
    if st.button("✨ 選書する", type="primary", use_container_width=True):
        if not user_input.strip():
            st.warning("リクエスト内容を入力してください。")
        else:
            st.session_state.history_titles = []
            with st.spinner("AIが選書中..."):
                results = fetch_recommendations(user_input, st.session_state.history_titles, target_mode)
                st.session_state.current_recommendations = results
                for book in results:
                    st.session_state.history_titles.append(book.get("title", ""))

# 「もう一回」ボタン（過去表示分を除外）
with col2:
    if st.button("🔄 別の本を見る", use_container_width=True):
        if not user_input.strip():
            st.warning("先にリクエスト内容を入力してください。")
        else:
            with st.spinner("別の本を探しています..."):
                results = fetch_recommendations(user_input, st.session_state.history_titles, target_mode)
                st.session_state.current_recommendations = results
                for book in results:
                    st.session_state.history_titles.append(book.get("title", ""))

# 結果表示
if st.session_state.current_recommendations:
    st.divider()
    st.subheader("📖 おすすめの5冊")
    
    for i, book in enumerate(st.session_state.current_recommendations, 1):
        title = book.get("title", "不明なタイトル")
        author = book.get("author", "不明な著者")
        reason = book.get("reason", "")
        keyword = book.get("search_keyword", f"{title} {author}")
        
        # 確実にヒットする検索URLを生成
        amazon_url = create_amazon_url(keyword, target_mode)
        
        with st.container():
            st.markdown(f"### {i}. {title}")
            st.caption(f"著者: {author}")
            st.write(reason)
            st.link_button(f"🔍 Amazonで『{title}』を探す ({target_mode})", amazon_url)
            st.write("")

# フッター・ステマ規制/規約表示
st.divider()
st.caption(
    "※当サービスはAmazonアソシエイト・プログラムに参加しており、"
    "紹介リンクを経由して購入や登録が行われた場合、報酬を得る場合があります。"
)
st.caption("※入力されたメッセージに個人情報（氏名や連絡先等）を含めないようご注意ください。")
