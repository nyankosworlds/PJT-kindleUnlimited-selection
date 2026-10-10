import json
import urllib.parse
import streamlit as st
from google import genai
from google.genai.errors import ServerError

# ---------------------------------------------------------
# 1. ページ初期設定（洗練されたミニマルなカスタムCSS）
# ---------------------------------------------------------
st.set_page_config(
    page_title="今日は何読む / 蔵書案内",
    page_icon="📖",
    layout="centered"
)

st.markdown("""
    <style>
        .block-container {
            padding-top: 2.5rem;
            padding-bottom: 3rem;
            max-width: 700px;
        }
        .stButton button {
            border-radius: 4px;
            font-weight: 400;
        }
        .stLinkButton button {
            border-radius: 4px;
        }
    </style>
""", unsafe_allow_html=True)

# AmazonアソシエイトID（ご自身のアソシエイトIDを取得後に書き換えてください）
ASSOCIATE_TAG = "your_tracking_id-22"

# ---------------------------------------------------------
# 2. セッション状態の初期化
# ---------------------------------------------------------
if "history_titles" not in st.session_state:
    st.session_state.history_titles = []  # 提案済みタイトルの除外リスト
if "current_recommendations" not in st.session_state:
    st.session_state.current_recommendations = [] # 現在表示中の結果

# ---------------------------------------------------------
# 3. UI表示（ヘッダー・入力フォーム）
# ---------------------------------------------------------
st.markdown("### 今日は何読む")
st.caption("気分や読書環境にあわせ、静かにひらく一冊をAIが選んでくれます。")

# 入力フォーム
user_input = st.text_area(
    "今の気分や、読みたいジャンルについてお聞かせください",
    placeholder="例：静かな夜に、少しずつページをめくれるようなエッセイを探しています。",
    height=80
)

# モード選択
target_mode = st.radio(
    "蔵書の対象",
    ["Kindle Unlimited 対象のみ", "Amazon 全体"],
    horizontal=True
)

# ---------------------------------------------------------
# 4. Amazon検索リンク生成関数
# ---------------------------------------------------------
def create_amazon_url(search_keyword, mode):
    encoded_keyword = urllib.parse.quote(search_keyword)
    if mode == "Kindle Unlimited 対象のみ":
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
# 5. 選書ロジック（サーバー過負荷の専用ハンドリング追加）
# ---------------------------------------------------------
def fetch_recommendations(prompt_text, exclude_list, mode):
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)

    mode_condition = ""
    if mode == "Kindle Unlimited 対象のみ":
        mode_condition = "【重要】Amazonの「Kindle Unlimited」の読み放題対象となっている確実な書籍のみを選定してください。少しでも対象か怪しい本は含めないでください。"
    else:
        mode_condition = "Amazonで広く流通している実在の書籍を選定してください。"

    system_instruction = f"""
    あなたは物静かで思慮深い独立系書店の店主です。
    ユーザーの入力内容と条件に基づいて、実在の書籍を「最大3冊（1〜3冊）」選定してください。
    {mode_condition}
    
    【重要】条件に完全に合致する確かな本のみを出力してください。数が足りない場合でも、無理に水増しして架空の本や条件外の本を含めることは絶対に避けてください（1冊だけでも構いません）。
    
    Amazonの検索窓で一発でヒットするように、各書籍の「正確な書籍タイトルと著者名」を組み合わせた検索キーワードを必ず `search_keyword` に設定してください。
    
    必ず以下のJSON配列フォーマット「のみ」を出力してください。Markdownのコードブロック（```json ... ```）や前後の解説文は含めないでください。

    [
      {{
        "title": "書籍タイトル",
        "author": "著者名",
        "reason": "選書の理由（100文字程度、落ち着いたトーンで）",
        "search_keyword": "Amazon検索用キーワード（例: 書籍タイトル 著者名）"
      }}
    ]
    """

    user_prompt = f"""
    【リクエスト】
    {prompt_text}

    【対象】
    {mode}

    【除外リスト（以下のタイトルの本は過去に提案済みのため、選ばないでください）】
    {", ".join(exclude_list) if exclude_list else "なし"}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
            config={
                "system_instruction": system_instruction,
                "response_mime_type": "application/json"
            }
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        data = json.loads(raw_text.strip())
        return data

    except ServerError:
        st.warning("現在、AIのサーバーが混み合っております。少し時間をおいてから、再度「この条件で探す」をお試しください。")
        return []
    except Exception as e:
        st.error(f"データの取得に失敗しました。少し時間をおいて再度お試しください。（詳細: {e}）")
        return []

# ---------------------------------------------------------
# 6. ボタン処理（新規選書）
# ---------------------------------------------------------
if st.button("この条件で探す", type="primary", use_container_width=True):
    if not user_input.strip():
        st.warning("リクエスト内容を入力してください。")
    else:
        st.session_state.history_titles = []
        with st.spinner("本棚を確認しています..."):
            results = fetch_recommendations(user_input, st.session_state.history_titles, target_mode)
            if results:
                st.session_state.current_recommendations = results
                for book in results:
                    st.session_state.history_titles.append(book.get("title", ""))

# ---------------------------------------------------------
# 7. 結果表示（2カラムレイアウト）
# ---------------------------------------------------------
if st.session_state.current_recommendations:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"**ご案内する本（{len(st.session_state.current_recommendations)}冊）**")
    st.markdown("---")
    
    for i, book in enumerate(st.session_state.current_recommendations, 1):
        title = book.get("title", "不明なタイトル")
        author = book.get("author", "不明な著者")
        reason = book.get("reason", "")
        keyword = book.get("search_keyword", f"{title} {author}")
        
        amazon_url = create_amazon_url(keyword, target_mode)
        
        with st.container():
            col_left, col_right = st.columns([1.2, 2.0])
            
            with col_left:
                st.markdown(f"**{title}**")
                st.caption(f"著：{author}")
                st.markdown("<br>", unsafe_allow_html=True)
                st.link_button("Amazonで詳細を見る", amazon_url, use_container_width=True)
            
            with col_right:
                st.caption("案内人より")
                st.write(reason)
            
            st.markdown("---")

    # -----------------------------------------------------
    # 8. 「別の本を見る」ボタン
    # -----------------------------------------------------
    if st.button("ほかの本も見てみる", use_container_width=True):
        if not user_input.strip():
            st.warning("先に入力内容をご確認ください。")
        else:
            with st.spinner("別の本を探しています..."):
                results = fetch_recommendations(user_input, st.session_state.history_titles, target_mode)
                if results:
                    st.session_state.current_recommendations = results
                    for book in results:
                        st.session_state.history_titles.append(book.get("title", ""))
                    st.rerun()

# フッター・規約表示
st.markdown("<br>", unsafe_allow_html=True)
st.caption(
    "当サービスはAmazonアソシエイト・プログラムに参加しています。"
    "紹介リンクを経由したご購入やご登録により、運営上の成果報酬を得ることがあります。"
)
