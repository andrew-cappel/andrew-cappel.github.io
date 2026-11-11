#!/usr/bin/env python3
"""Builds bythebook/books.json: public-domain classics with 5 quotes each (hardest first).

Every quote is checked against the book's full text on Project Gutenberg and replaced with the
exact wording found there; quotes that can't be found are dropped and topped up with real
sentences from the book. Run: python3 scripts/books.py
"""
import difflib, json, random, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "bythebook" / "books.json"
UA = "ByTheBookBuilder/1.0 (daily book quiz)"

# title | author | year | pages (common edition) | key character (never the title name) | quotes, hardest -> easiest
B = [
 ("Pride and Prejudice", "Jane Austen", 1813, 432, "Mr. Darcy", ["I could easily forgive his pride, if he had not mortified mine.", "There is a stubbornness about me that never can bear to be frightened at the will of others.", "You must allow me to tell you how ardently I admire and love you.", "My good opinion once lost, is lost for ever.", "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife."]),
 ("Moby-Dick", "Herman Melville", 1851, 635, "Captain Ahab", ["I know not all that may be coming, but be it what it will, I'll go to it laughing.", "Better sleep with a sober cannibal than a drunken Christian.", "from hell's heart I stab at thee; for hate's sake I spit my last breath at thee.", "It is not down in any map; true places never are.", "Call me Ishmael."]),
 ("Frankenstein", "Mary Shelley", 1818, 280, "Robert Walton", ["Nothing is so painful to the human mind as a great and sudden change.", "Beware; for I am fearless, and therefore powerful.", "I was benevolent and good; misery made me a fiend.", "I beheld the wretch—the miserable monster whom I had created.", "It was on a dreary night of November that I beheld the accomplishment of my toils."]),
 ("Dracula", "Bram Stoker", 1897, 418, "Jonathan Harker", ["We learn from failure, not from success!", "I never drink—wine.", "Listen to them—the children of the night. What music they make!", "Welcome to my house! Enter freely and of your own will!", "I bid you welcome, Mr. Harker, to my house."]),
 ("Jane Eyre", "Charlotte Brontë", 1847, 532, "Edward Rochester", ["I would always rather be happy than dignified.", "The more solitary, the more friendless, the more unsustained I am, the more I will respect myself.", "I am no bird; and no net ensnares me: I am a free human being with an independent will.", "There was no possibility of taking a walk that day.", "Reader, I married him."]),
 ("Wuthering Heights", "Emily Brontë", 1847, 416, "Heathcliff", ["Treachery and violence are spears pointed at both ends; they wound those who resort to them worse than their enemies.", "I have dreamt in my life, dreams that have stayed with me ever after, and changed my ideas.", "Be with me always—take any form—drive me mad!", "I cannot live without my life! I cannot live without my soul!", "Whatever our souls are made of, his and mine are the same."]),
 ("Alice's Adventures in Wonderland", "Lewis Carroll", 1865, 200, "the White Rabbit", ["I can't go back to yesterday, because I was a different person then.", "Who in the world am I? Ah, that's the great puzzle!", "we're all mad here. I'm mad. You're mad.", "Curiouser and curiouser!", "Off with her head!"]),
 ("The Adventures of Sherlock Holmes", "Arthur Conan Doyle", 1892, 307, "Dr. John Watson", ["Life is infinitely stranger than anything which the mind of man could invent.", "It is a capital mistake to theorize before one has data.", "You see, but you do not observe.", "I am lost without my Boswell.", "To Sherlock Holmes she is always the woman."]),
 ("The Great Gatsby", "F. Scott Fitzgerald", 1925, 180, "Nick Carraway", ["I was within and without, simultaneously enchanted and repelled by the inexhaustible variety of life.", "They were careless people, Tom and Daisy—they smashed up things and creatures and then retreated back into their money", "Can't repeat the past? Why of course you can!", "In my younger and more vulnerable years my father gave me some advice that I've been turning over in my mind ever since.", "So we beat on, boats against the current, borne back ceaselessly into the past."]),
 ("A Tale of Two Cities", "Charles Dickens", 1859, 448, "Sydney Carton", ["A multitude of people, and yet a solitude.", "Crush humanity out of shape once more, under similar hammers, and it will twist itself into the same tortured forms.", "I wish you to know that you have been the last dream of my soul.", "It is a far, far better thing that I do, than I have ever done", "It was the best of times, it was the worst of times"]),
 ("Great Expectations", "Charles Dickens", 1861, 505, "Pip", ["Heaven knows we need never be ashamed of our tears, for they are rain upon the blinding dust of earth", "I was too cowardly to do what I knew to be right, as I had been too cowardly to avoid doing what I knew to be wrong.", "I loved her against reason, against promise, against peace, against hope, against happiness, against all discouragement that could be.", "Suffering has been stronger than all other teaching, and has taught me to understand what your heart used to be.", "my infant tongue could make of both names nothing longer or more explicit than Pip."]),
 ("A Christmas Carol", "Charles Dickens", 1843, 104, "Ebenezer Scrooge", ["I wear the chain I forged in life", "Mankind was my business.", "I will honour Christmas in my heart, and try to keep it all the year.", "God bless Us, Every One!", "Bah! Humbug!"]),
 ("Oliver Twist", "Charles Dickens", 1838, 608, "Fagin", ["There is a passion for hunting something deeply implanted in the human breast.", "Some people are nobody's enemies but their own", "the law is a ass—a idiot.", "has asked for more!", "Please, sir, I want some more."]),
 ("Treasure Island", "Robert Louis Stevenson", 1883, 292, "Long John Silver", ["if you keep on drinking rum, the world will soon be quit of a very dirty scoundrel!", "Drink and the devil had done for the rest", "Them that die'll be the lucky ones!", "Pieces of eight! pieces of eight!", "Fifteen men on the dead man's chest— Yo-ho-ho, and a bottle of rum!"]),
 ("The Time Machine", "H. G. Wells", 1895, 118, "Weena", ["It is a law of nature we overlook, that intellectual versatility is the compensation for change, danger, and trouble.", "Nature never appeals to intelligence until habit and instinct are useless.", "There is no difference between Time and any of the three dimensions of Space except that our consciousness moves along it.", "I grieved to think how brief the dream of the human intellect had been.", "the Eloi, like the Carlovingian kings, had decayed to a mere beautiful futility."]),
 ("The War of the Worlds", "H. G. Wells", 1898, 192, "Ogilvy the astronomer", ["And we men, the creatures who inhabit this earth, must be to them at least as alien and lowly as are the monkeys and lemurs to us.", "intellects vast and cool and unsympathetic, regarded this earth with envious eyes", "Ulla, ulla, ulla, ulla", "No one would have believed in the last years of the nineteenth century that this world was being watched keenly and closely", "The chances against anything manlike on Mars are a million to one"]),
 ("The Picture of Dorian Gray", "Oscar Wilde", 1890, 254, "Lord Henry Wotton", ["The only way to get rid of a temptation is to yield to it.", "There is only one thing in the world worse than being talked about, and that is not being talked about.", "Behind every exquisite thing that existed, there was something tragic.", "every portrait that is painted with feeling is a portrait of the artist, not of the sitter.", "If it were I who was to be always young, and the picture that was to grow old!"]),
 ("The Count of Monte Cristo", "Alexandre Dumas", 1844, 1276, "Edmond Dantès", ["there is neither happiness nor misery in the world; there is only the comparison of one state with another, nothing more.", "Hatred is blind; rage carries you away; and he who pours out vengeance runs the risk of tasting a bitter draught.", "Moral wounds have this peculiarity—they may be hidden, but they never close; always painful, always ready to bleed when touched", "I am not proud, but I am happy; and happiness blinds, I think, more than pride.", "all human wisdom is contained in these two words,—'Wait and hope.'"]),
 ("Peter Pan", "J. M. Barrie", 1911, 192, "Wendy Darling", ["To die will be an awfully big adventure.", "Every time a child says, 'I don't believe in fairies,' there is a fairy somewhere that falls down dead.", "Second to the right, and straight on till morning.", "If you believe, clap your hands!", "All children, except one, grow up."]),
 ("The Wonderful Wizard of Oz", "L. Frank Baum", 1900, 154, "Dorothy", ["No matter how dreary and gray our homes are, we people of flesh and blood would rather live there than in any other country, be it ever so beautiful.", "I shall take the heart, for brains do not make one happy, and happiness is the best thing in the world.", "All you need is confidence in yourself.", "There is no place like home.", "the road to the City of Emeralds is paved with yellow brick"]),
 ("Anne of Green Gables", "L. M. Montgomery", 1908, 320, "Marilla Cuthbert", ["Isn't it nice to think that tomorrow is a new day with no mistakes in it yet?", "It's so easy to be wicked without knowing it, isn't it?", "Kindred spirits are not so scarce as I used to think.", "I'm so glad I live in a world where there are Octobers.", "Will you please call me Cordelia?"]),
 ("The Secret Garden", "Frances Hodgson Burnett", 1911, 331, "Mary Lennox", ["At first people refuse to believe that a strange new thing can be done, then they begin to hope it can be done", "Where you tend a rose, my lad, A thistle cannot grow.", "If you look the right way, you can see that the whole world is a garden.", "I am going to live forever and ever and ever!", "everybody said she was the most disagreeable-looking child ever seen."]),
 ("The Call of the Wild", "Jack London", 1903, 172, "Buck", ["There is an ecstasy that marks the summit of life, and beyond which life cannot rise.", "the law of club and fang", "He was a killer, a thing that preyed, living on the things that lived", "he sang a song of the younger world, which is the song of the pack.", "Buck did not read the newspapers, or he would have known that trouble was brewing"]),
 ("Strange Case of Dr Jekyll and Mr Hyde", "Robert Louis Stevenson", 1886, 88, "Gabriel John Utterson", ["I incline to Cain's heresy", "man is not truly one, but truly two.", "I learned to recognise the thorough and primitive duality of man", "I shall be Mr. Seek.", "the drug had no discriminating action; it was neither diabolical nor divine"]),
 ("Robinson Crusoe", "Daniel Defoe", 1719, 320, "Friday", ["fear of danger is ten thousand times more terrifying than danger itself", "it is never too late to be wise", "I was born in the year 1632, in the city of York, of a good family", "the print of a man's naked foot on the shore", "his name should be Friday, which was the day I saved his life"]),
 ("Gulliver's Travels", "Jonathan Swift", 1726, 306, "the Lilliputians", ["Undoubtedly philosophers are in the right, when they tell us that nothing is great or little otherwise than by comparison.", "the Big-endians", "I lay all this while, as the reader may believe, in great uneasiness.", "the Houyhnhnms", "Yahoos"]),
 ("The Scarlet Letter", "Nathaniel Hawthorne", 1850, 272, "Hester Prynne", ["No man, for any considerable period, can wear one face to himself and another to the multitude, without finally getting bewildered as to which may be the true.", "She had not known the weight until she felt the freedom.", "the elf-child", "the letter A", "On the breast of her gown, in fine red cloth, surrounded with an elaborate embroidery and fantastic flourishes of gold thread, appeared the letter A."]),
 ("Little Women", "Louisa May Alcott", 1868, 759, "Jo March", ["I'm not afraid of storms, for I'm learning how to sail my ship.", "Housekeeping ain't no joke.", "I'd rather take coffee than compliments just now.", "I like good strong words that mean something.", "Christmas won't be Christmas without any presents"]),
 ("The Adventures of Tom Sawyer", "Mark Twain", 1876, 274, "Becky Thatcher", ["Work consists of whatever a body is obliged to do, and that Play consists of whatever a body is not obliged to do.", "in order to make a man or a boy covet a thing, it is only necessary to make the thing difficult to attain.", "Injun Joe", "whitewash", "Aunt Polly"]),
 ("Adventures of Huckleberry Finn", "Mark Twain", 1884, 366, "Jim", ["Hain't we got all the fools in town on our side? and ain't that a big enough majority in any town?", "All right, then, I'll go to hell", "It's lovely to live on a raft.", "You don't know about me without you have read a book by the name of The Adventures of Tom Sawyer", "I reckon I got to light out for the Territory ahead of the rest"]),
 ("Metamorphosis", "Franz Kafka", 1915, 70, "Gregor Samsa", ["I cannot make you understand.", "Was he an animal if music could captivate him so?", "He felt as if the way to the unknown nourishment he longed for was coming to light.", "What's happened to me?", "he found himself transformed in his bed into a horrible vermin."]),
 ("Heart of Darkness", "Joseph Conrad", 1899, 96, "Kurtz", ["We live, as we dream—alone.", "The mind of man is capable of anything", "Exterminate all the brutes!", "Mistah Kurtz—he dead.", "The horror! The horror!"]),
 ("Emma", "Jane Austen", 1815, 474, "George Knightley", ["One half of the world cannot understand the pleasures of the other.", "Silly things do cease to be silly if they are done by sensible people in an impudent way.", "If I loved you less, I might be able to talk about it more.", "Badly done, Emma, badly done!", "handsome, clever, and rich, with a comfortable home and happy disposition"]),
 ("The Hound of the Baskervilles", "Arthur Conan Doyle", 1902, 256, "Sherlock Holmes", ["The world is full of obvious things which nobody by any chance ever observes.", "There is nothing more stimulating than a case where everything goes against you.", "the moor", "Grimpen Mire", "Mr. Holmes, they were the footprints of a gigantic hound!"]),
]

def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(5 * (i + 1))

IDS = {"Pride and Prejudice": 1342, "Moby-Dick": 2701, "Frankenstein": 84, "Dracula": 345, "Jane Eyre": 1260, "Wuthering Heights": 768,
 "Alice's Adventures in Wonderland": 11, "The Adventures of Sherlock Holmes": 1661, "The Great Gatsby": 64317, "A Tale of Two Cities": 98,
 "Great Expectations": 1400, "A Christmas Carol": 46, "Oliver Twist": 730, "Treasure Island": 120, "The Time Machine": 35, "The War of the Worlds": 36,
 "The Picture of Dorian Gray": 174, "The Count of Monte Cristo": 1184, "Peter Pan": 16, "The Wonderful Wizard of Oz": 55, "Anne of Green Gables": 45,
 "The Secret Garden": 113, "The Call of the Wild": 215, "Strange Case of Dr Jekyll and Mr Hyde": 43, "Robinson Crusoe": 521, "Gulliver's Travels": 829,
 "The Scarlet Letter": 25344, "Little Women": 514, "The Adventures of Tom Sawyer": 74, "Adventures of Huckleberry Finn": 76, "Metamorphosis": 5200,
 "Heart of Darkness": 219, "Emma": 158, "The Hound of the Baskervilles": 2852}

def gutenberg(title, author):
    """Full text straight from Project Gutenberg by catalogue number (checked against the title line)."""
    n = IDS[title]
    t = get(f"https://www.gutenberg.org/cache/epub/{n}/pg{n}.txt").decode("utf-8", "replace")
    key = max(re.findall(r"[A-Za-z]{4,}", title), key=len).lower()
    if key not in t[:3000].lower(): raise ValueError(f"#{n} is not {title}")
    return t

norm = lambda s: re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("_", "")).strip()
words = lambda s: set(re.findall(r"[a-z']{4,}", s.lower()))

def verify(text, q):
    """Exact wording of q as it appears in the book, or None."""
    t, qq = norm(text), norm(q)
    i = t.lower().find(qq.lower())
    if i >= 0: return t[i:i + len(qq)]
    sents = re.split(r"(?<=[.!?\"'])\s+", t); qw = words(qq); best, score = None, 0
    for s in sents:
        if len(s) > 400 or not qw or len(qw & words(s)) < max(1, len(qw) * .5): continue
        r = difflib.SequenceMatcher(None, qq.lower(), s.lower()).ratio()
        if r > score: best, score = s, r
    return best if score >= .72 else None

def fillers(text, n, seed):
    t = norm(text); sents = [s for s in re.split(r"(?<=[.!?])\s+", t) if 70 <= len(s) <= 170 and not re.search(r"CHAPTER|Gutenberg|[\[\]*]", s)]
    random.Random(seed).shuffle(sents); return sents[:n]

def main():
    out = []
    for title, author, year, pages, key, qs in B:
        print(title, flush=True)
        try: text = gutenberg(title, author)
        except Exception as e: print("  !! no text:", e); continue
        a, b = text.find("*** START"), text.find("*** END")
        text = text[text.find("\n", a) if a >= 0 else 0: b if b > 0 else None]
        good = []
        for q in qs:
            v = verify(text, q)
            print(("  ok   " if v else "  DROP ") + (v or q)[:90], flush=True)
            if v and len(v) <= 320: good.append(v)
        good = fillers(text, 5 - len(good), title) + good   # top up at the hard end with real sentences
        out.append({"title": title, "author": author, "year": year, "pages": pages, "key": key, "quotes": good[:5]})
        time.sleep(1)
    OUT.parent.mkdir(exist_ok=True); OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0))
    print("wrote", len(out), "books")

if __name__ == "__main__":
    main()
