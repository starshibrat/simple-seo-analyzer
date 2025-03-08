import requests
import unittest
from pprint import pprint
from bs4 import BeautifulSoup
from enum import Enum
import re
from urllib.parse import urljoin
import pyphen
import nltk
import sys
from nltk.tokenize import sent_tokenize
from xml.dom import minidom
import datetime

url = "https://requests.readthedocs.io/en/latest/"

class Status(Enum):
    BAD = 0
    GOOD = 1

    def __str__(self):
        if self.value == 0:
            return "BAD"
        return "GOOD"

class State:
    def __init__(self, status: Status, desc: str, ele: str):
        self.status = status
        self.desc = desc
        self.ele = ele
    
    def __str__(self):
        return f"Status: {self.status}\nDescription: {self.desc}\nElement: {self.ele}"


def relative_path(link: str) -> bool:
    return not (link.startswith("https://") or link.startswith("http://"))

def check_link(link: str, parent: str = None):
    try:
        if relative_path(link):
            link = urljoin(parent, link)

        r = requests.get(link)
        if r.status_code == 200:
            state = State(Status.GOOD, f"link is working", link)
            return state
        else:
            state = State(Status.BAD, f"link is not working i.e RESPONSE CODE != 200", link)
            return state
    except Exception as e:
        return e

def check_h1(soup: BeautifulSoup):
    try:
        h1 = soup.find_all("h1")

        if len(h1) > 1 or len(h1) == 0:
            state = State(Status.BAD, f"h1 is not exist or more than one", h1)
        else:
            state = State(Status.GOOD, f"h1 used once", h1)
        return state
    except Exception as e:
        return e
    
def check_href(soup: BeautifulSoup, url: str=None):
    try:
        elements = soup.find_all()
        states = []
        for ele in elements:
            if ele.has_attr("href"):
                val = ele.get("href")
                state = check_link(val , url)
                states.append(state)

        return states
    except Exception as e:
        return e
    
def check_headings(soup: BeautifulSoup):
    try:
        elements = soup.find_all(re.compile('^h[1-6]$'))
        print(elements)
        states = []

        return states
    except Exception as e:
        return e

def check_alt_img(soup: BeautifulSoup):
    try:
        img = soup.find_all("img")
        img_states = []

        for i in img:
            if i.has_attr("alt"):
                state = State(Status.GOOD, "has alt attributes", i)
            else:
                state = State(Status.BAD, "has no alt attributes", i)
            img_states.append(state)

        return img_states
    except Exception as e:
        return e
    
def check_meta(soup: BeautifulSoup):
    try:
        meta = soup.find("meta", attrs={"name": "description"})
        
        if not meta:
            return State(Status.BAD, "the meta description doesn't exist", "")

        if meta["content"]:
            meta_content = meta["content"]
            meta_len = len(meta_content)

            if meta_len < 130 or meta_len > 160:
                return State(Status.BAD, "the meta description recommended length is 130-160", meta_content)
            else:
                return State(Status.GOOD, "the meta description length is between 130 and 160", meta_content)
    except Exception as e:
        return e

def check_title(soup: BeautifulSoup):
    try:
        element = soup.find("title")
        ele_txt = len(element.text)
        
        if ele_txt >= 50 and ele_txt <= 60:
            return State(Status.GOOD, "title length between 50-60", element)
        else:
            return State(Status.BAD, "title length not between 50-60", element)
    except Exception as e:
        return e

def count_syllable(word: str, lang):
    word = word.lower()
    dic = pyphen.Pyphen(lang=lang)
    res = dic.inserted(word).split("-")
    return len(res)

def para_to_word_list(para):
    return re.findall("[a-zA-Z_]+", para)

def count_word(word: str):
    res = re.findall("[a-zA-Z_]+", word)
    return len(res)

def count_sentences(word: str):
    res = sent_tokenize(word)
    return len(res)

def check_readability(txt: str, lang: str="en_US"):
    tw = count_word(txt)
    ts = count_sentences(txt)
    tsy = 0

    for w in para_to_word_list(txt):
        c = count_syllable(w, lang)
        tsy += c

    # print(f"tw: {tw}\nts: {ts}\ntsy: {tsy}")

    return 206.835 - 1.015*(tw/ts) - 84.6*(tsy/tw)

class Freq(Enum):
    ALWAYS = 0,
    HOURLY = 1,
    DAILY = 2,
    WEEKLY = 3,
    MONTHLY = 4,
    YEARLY = 5,
    NEVER = 6

class SMEntity:
    def __init__(self, loc: str, lastmod: str=None, changefreq: Freq=None, priority: float=None):
        self.loc = loc
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority

def match_freq(freq: Freq):
    match(freq):
        case Freq.ALWAYS:
            return "always"
        case Freq.HOURLY:
            return "hourly"
        case Freq.DAILY:
            return "daily"
        case Freq.WEEKLY:
            return "weekly"
        case Freq.MONTHLY:
            return "monthly"
        case Freq.YEARLY:
            return "yearly"
        case Freq.NEVER:
            return "never"
        case _:
            return ""

def validate_date(str):
    try:
        if str == datetime.datetime.strptime(str, "%Y-%m-%d").strftime('%Y-%m-%d'):
            return str
    except ValueError:
        return datetime.datetime.now().strftime('%Y-%m-%d')

def create_xml_sitemap(urls: list[SMEntity], filename="sitemap.xml"):
    doc = minidom.Document()

    root = doc.createElement('urlset')
    root.setAttribute("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    doc.appendChild(root)

    for u in urls:
        url = doc.createElement('url')
        loc = doc.createElement('loc')
        locTxt = doc.createTextNode(u.loc)
        loc.appendChild(locTxt)
        url.appendChild(loc)

        if u.lastmod is not None:
            the_date = validate_date(u.lastmod)
            lastmod = doc.createElement('lastmod')
            lastmodTxt = doc.createTextNode(the_date)
            lastmod.appendChild(lastmodTxt)
            url.appendChild(lastmod)

        freq = match_freq(u.changefreq)
        if freq != "":
            changefreq = doc.createElement('changefreq')
            changefreqTxt = doc.createTextNode(freq)
            changefreq.appendChild(changefreqTxt)
            url.appendChild(changefreq)

        if u.priority is not None and u.priority >= 0.0 and u.priority <= 1.0:
            priority = doc.createElement("priority")
            priorityTxt = doc.createTextNode("{:.1f}".format(u.priority))
            priority.appendChild(priorityTxt)
            url.appendChild(priority)

        root.appendChild(url)

    xml_str = doc.toprettyxml(indent="  ")
    with open(filename, "w") as f:
        f.write(xml_str)


class TestFeatures(unittest.TestCase):
    def init_soup(self):
        r = requests.get(url)
        html_doc = r.text
        return BeautifulSoup(html_doc, 'html.parser')

    def test_get_page(self):
        try:
            r = requests.get(url)
        except Exception as e:
            self.fail(f"Exception: {e}")
    def test_beautify(self):
        try:
            r = requests.get(url)
            html_doc = r.text
            soup = BeautifulSoup(html_doc, 'html.parser')
        except Exception as e:
            self.fail(f"Exception: {e}")

    def test_check_h1(self):
        try:
            r = requests.get(url)
            html_doc = r.text
            soup = self.init_soup()
            check_h1(soup)
        except Exception as e:
            self.fail(f"Exception: {e}")

    def test_check_alt_img(self):
        try:
            soup = self.init_soup()
            check = check_alt_img(soup)
        except Exception as e:
            self.fail(f"Exception: {e}")
    
    @unittest.skip("Large web will take too long")
    def test_check_href(self):
        try:
            soup = self.init_soup()
            check_href(soup)
        except Exception as e:
            self.fail(f"Exception: {e}")

    @unittest.skip("Soon to be implemented")
    def test_check_headings(self):
        try:
            soup = self.init_soup()
            check = check_headings(soup)
        except Exception as e:
            self.fail(f"Exception: {e}")

    def test_check_meta(self):
        try:
            soup = self.init_soup()
            check = check_meta(soup)
        except Exception as e:
            self.fail(f"Exception: {e}")
    
    def test_title(self):
        try:
            soup = self.init_soup()
            check = check_title(soup)
            # print(check)
        except Exception as e:
            self.fail(f"Exception: {e}")

    def test_count_syllable(self):
        try:
            word = "menyapu"
            lang = "id_ID"
            cnt = count_syllable(word, lang)
            self.assertEqual(cnt, 3)
        except Exception as e:
            self.fail(f"Exception: {e}")

    def test_count_word(self):
        word = "The world is heading towards the end. And I am here for it."
        cnt = count_word(word)
        self.assertEqual(cnt, 13)

    def test_count_sentences(self):
        sentences = "When the sky falls, I hope to not witness. I'm going to the place where no one else goes. The prophecy of De'huzman"
        cnt = count_sentences(sentences)
        self.assertEqual(cnt, 3)
    
    def test_readability(self):
        try:
            para = "The Flesch–Kincaid readability tests are readability tests designed to indicate how difficult a passage in English is to understand. There are two tests: the Flesch Reading-Ease, and the Flesch–Kincaid Grade Level. Although they use the same core measures (word length and sentence length), they have different weighting factors. The results of the two tests correlate approximately inversely: a text with a comparatively high score on the Reading Ease test should have a lower score on the Grade-Level test. Rudolf Flesch devised the Reading Ease evaluation; somewhat later, he and J. Peter Kincaid developed the Grade Level evaluation for the United States Navy. "
            lang = "en_US"
            score = check_readability(para, lang)
            print(score)
        except Exception as e:
            self.fail(f"Exception: {e}")

    def test_create_xml(self):
        try:
            links = [
                SMEntity("https://www.sitemaps.org/", changefreq=Freq.HOURLY, priority=2.3, lastmod='2023-04-10'),
                SMEntity("https://docs.python.org/", priority=0.8),
                SMEntity("https://stackoverflow.com/", changefreq=Freq.DAILY, priority=0.4, lastmod='ascmk')
            ]
            create_xml_sitemap(links)
        except Exception as e:
            self.fail(f"Exception: {e}")

def check_url_input(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")

def exit_fail():
    sys.exit(1)

def h1_ui(soup: BeautifulSoup):
    print("Checking h1....\n")
    print(check_h1(soup))

def href_ui(soup: BeautifulSoup):
    print("Checking href links....")
    for st in check_href(soup):
        print("\n")
        print(st)

def img_ui(soup: BeautifulSoup):
    print("Checking img....")
    for st in check_alt_img(soup):
        print("\n")
        print(st)

def meta_ui(soup: BeautifulSoup):
    print("Checking meta....")
    print("\n")
    print(check_meta(soup))

def title_ui(soup: BeautifulSoup):
    print("Checking title....")
    print("\n")
    print(check_title(soup))

def readability_ui():
    print("Currently en_US is the most accurate one.")
    lang = input("Language (code): ")
    inp = input("Enter text: ")
    print("\nScore: ", check_readability(inp, lang))

def sitemap_ui():
    print("Sitemap Generator")
    inp = int(input("How many link? "))
    urls = []
    for i in range(inp):
        print("\m")
        loc = input("loc: ")
        lastmod = input("lastmod (YYYY-MM-DD): (just enter if empty) ")

        if lastmod == "":
            lastmod = None

        print("changefreq value:\n1. Always 2. Hourly 3. Daily 4. Weekly 5. Monthly 6. Yearly 7. Never\n")
        changefreq = input("changefreq: (just enter if empty)")

        match changefreq:
            case "1":
                changefreq = Freq.ALWAYS
            case "2":
                changefreq = Freq.HOURLY
            case "3":
                changefreq = Freq.DAILY
            case "4":
                changefreq = Freq.WEEKLY
            case "5":
                changefreq = Freq.MONTHLY
            case "6":
                changefreq = Freq.YEARLY
            case "7":
                changefreq = Freq.NEVER
            case _:
                changefreq = None
        
        try:
            priority = float(input("priority (0.0 - 1.0): (just enter if empty)"))
        except Exception as e:
            priority = None

        sm = SMEntity(loc, lastmod, changefreq, priority)
        urls.append(sm)

    create_xml_sitemap(urls)

def ui():
    print("Simple SEO Audit Tools\n\n")

    print("1. Web page\n2. Other")

    first = input()

    if first == "1":
        link = input("Enter link: ")

        if not check_url_input(link):
            print("http and https only")
            exit_fail()

        try:
            check_link(link)
            r = requests.get(link)
            html_doc = r.text
            soup = BeautifulSoup(html_doc, 'html.parser')
        except Exception as e:
            print(f"Exception: {e}")
            exit_fail()

        while(True):
            print("""\n
            1. Check h1
            2. Check href links
            3. Check Img
            4. Check Meta
            5. Check Title
            6. Check Content Readability
            """)
            inp = input(">>> ")
            print("\n")
            match inp:
                case "1":
                    h1_ui(soup)
                case "2":
                    href_ui(soup)
                case "3":
                    img_ui(soup)
                case "4":
                    meta_ui(soup)
                case "5":
                    title_ui(soup)
                case "6":
                    readability_ui()
                case _:
                    break
    if first == "2":
        while(True):
            print("""\n
                1. Check Content Readability
                2. Sitemap (XML) Generator
                """)
            inp = input(">>> ")
            print("\n")
            match inp:
                case "1":
                    readability_ui()
                case "2":
                    sitemap_ui()
                case _:
                    break
    
    print("Program Over.")

if __name__ == '__main__':
    # unittest.main()
    ui()