"""
Tests for Parsers
"""

import pytest
from bs4 import BeautifulSoup
from scraper.books_parser import Parser as BooksParser
from scraper.quotes_parser import Parser as QuotesParser
from scraper.jobs_parser import Parser as JobsParser


def test_books_parser_columns():
    """Test books parser returns expected columns."""
    parser = BooksParser()
    columns = parser.get_columns()
    assert "title" in columns
    assert "price" in columns
    assert "rating" in columns


def test_books_parser_parse_listing():
    """Test books parser extracts data correctly from HTML."""
    html = '''
    <ul class="breadcrumb"><li><a href="">Home</a></li><li><a href="">Books</a></li><li>Fiction</li></ul>
    <article class="product_pod">
        <div class="image_container"><a href="book.html"><img src="img.jpg" class="thumbnail"></a></div>
        <p class="star-rating Three"><i></i><i></i><i></i><i></i><i></i></p>
        <h3><a href="book.html" title="A Great Book">A Great Book</a></h3>
        <div class="product_price">
            <p class="price_color">£51.77</p>
            <p class="instock availability"><i class="icon-ok"></i>In stock</p>
        </div>
    </article>
    '''
    soup = BeautifulSoup(html, "html.parser")
    parser = BooksParser()
    records = parser.parse_listing(soup, "https://books.toscrape.com/catalogue/category/books/fiction_10/index.html")

    assert len(records) == 1
    book = records[0]
    assert book["title"] == "A Great Book"
    assert book["price"] == "51.77"
    assert book["rating"] == 3
    assert book["availability"] == "In stock"
    assert book["category"] == "Fiction"


def test_quotes_parser_parse_listing():
    """Test quotes parser extracts data correctly from HTML."""
    html = '''
    <div class="quote">
        <span class="text">"The world as we have created it is a process of our thinking."</span>
        <span>by <small class="author">Albert Einstein</small>
        <a href="/author/Albert-Einstein">(about)</a></span>
        <div class="tags">
            <a class="tag" href="/tag/change/page/1/">change</a>
            <a class="tag" href="/tag/deep-thoughts/page/1/">deep-thoughts</a>
        </div>
    </div>
    '''
    soup = BeautifulSoup(html, "html.parser")
    parser = QuotesParser()
    records = parser.parse_listing(soup, "https://quotes.toscrape.com/page/1/")

    assert len(records) == 1
    quote = records[0]
    assert quote["quote"] == "The world as we have created it is a process of our thinking."
    assert quote["author"] == "Albert Einstein"
    assert quote["tags"] == "change, deep-thoughts"


def test_jobs_parser_columns():
    """Test jobs parser template."""
    parser = JobsParser()
    columns = parser.get_columns()
    assert "job_title" in columns
    assert "company" in columns
