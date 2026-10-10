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
    placeholder="例：仕事で疲れたのでサクッと読めて癒やされるエッセイが読みたい。最近は刺し子をしながら流し読みできるような本が好き。",
    height=100
)

# モード選択
target_mode = st.radio(
    "対象エリア",
    ["Kindle Unlimited対象のみ", "Amazon全体"],
    horizontal=True
)

# ---------------------------------------------------------
# 4. Amazonリンク整形用関数
# ---------------------------------------------------------
def format_amazon_url(ai_url, title, author, mode):
    # AIが実際のAmazon商品URLを取得できている場合、アソシエイトタグを綺麗に付与
    if ai_url and "amazon.co.jp" in ai_url:
        # すでにタグがある場合は置換、なければ追加
        parsed_url = urllib.parse.urlparse(ai_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params['tag'] = [ASSOCIATE_TAG]
        
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        cleaned_url = urllib.parse.urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        return cleaned_url
    else:
        # フォールバック：確実な検索結果URL
        encoded_keyword = urllib.parse.quote(f"{title} {author}")
        if mode == "Kindle Unlimited対象のみ":
            return (
                f"https://www.amazon.co.jp/s?k={encoded_keyword}"
                f"&i=digital-text"
                f"&rh=p_n_feature_nineteen_browse-bin%3A3169286051"
                f"&tag={ASSOCIATE_TAG}"
            )
        else:
            return f"https://www.amazon.co.jp/s?k={encoded_keyword}&tag={ASSOCIATE_TAG}"

# ---------------------------------------------------------
# 5. AI選書ロジック（Google検索で本物のURLを取得）
# ---------------------------------------------------------
def fetch_recommendations(prompt_text, exclude_list, mode):
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)

    system_instruction = """
    あなたは親切で優秀なプロの選書家です。
    ユーザーの入力内容に基づいて、日本のAmazonに実際に存在する実在の書籍を5冊選定してください。
    【重要】必ずGoogle検索ツールを使用して、Web上のAmazonに掲載されている実際の書籍ページ（商品URL）を確認・取得してください。架空の本は絶対に含めないでください。
    以下の指定されたJSONフォーマットのみを出力してください。余計な解説文やMarkdownの装飾は含めないでください。

    【出力JSONフォーマット】
    [
      {
        "title": "書籍タイトル",
        "author": "著者名",
        "reason": "おすすめの理由（100文字程度）",
        "amazon_url": "Google検索で見つけたAmazonの実際の個別商品ページURL"
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

    # Google検索（Grounding）を有効化
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=user_prompt,
        config={
            "system_instruction": system_instruction,
            "response_mime_type": "application/json",
            "tools": [{"google_search": {}}]
        }
    )

    try:
        data = json.loads(response.text)
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
            with st.spinner("AIがWeb上の実在書籍と商品ページを検索中..."):
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
        raw_url = book.get("amazon_url", "")
        
        # リンクの整形とアソシエイトタグ付与
        amazon_url = format_amazon_url(raw_url, title, author, target_mode)
        
        with st.container():
            st.markdown(f"### {i}. {title}")
            st.caption(f"著者: {author}")
            st.write(reason)
            st.link_button(f"📖 Amazonで詳細を見る ({target_mode})", amazon_url)
            st.write("")

# フッター・ステマ規制/規約表示
st.divider()
st.caption(
    "※当サービスはAmazonアソシエイト・プログラムに参加しており、"
    "紹介リンクを経由して購入や登録が行われた場合、報酬を得る場合があります。"
)
st.caption("※入力されたメッセージに個人情報（氏名や連絡先等）を含めないようご注意ください。")
