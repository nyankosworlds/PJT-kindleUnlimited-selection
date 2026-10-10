# ---------------------------------------------------------
# 5. Amazonリンク生成関数（ISBNの有効性チェック付き）
# ---------------------------------------------------------
def create_amazon_url(isbn, title, author, mode):
    clean_isbn = "".join(filter(str.isdigit, str(isbn)))
    
    # 正しい10桁、または978から始まる13桁のISBNであるかチェック
    is_valid_isbn = False
    asin = ""
    
    if len(clean_isbn) == 10:
        asin = clean_isbn
        is_valid_isbn = True
    elif len(clean_isbn) == 13 and clean_isbn.startswith("978"):
        # 13桁のISBNからAmazonのASIN（10桁）に変換（先頭の978を外し、チェックディジットを除外）
        asin = clean_isbn[3:12]
        is_valid_isbn = True

    # 正しいISBNが取得できている場合のみ直接商品ページ（/dp/）へ飛ばす
    if is_valid_isbn and len(asin) == 9:
        url = f"https://www.amazon.co.jp/dp/{asin}?tag={ASSOCIATE_TAG}"
    else:
        # 不完全なISBNや取得できなかった場合は、確実なキーワード検索（タイトル+著者名）にフォールバック
        encoded_keyword = urllib.parse.quote(f"{title} {author}")
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
