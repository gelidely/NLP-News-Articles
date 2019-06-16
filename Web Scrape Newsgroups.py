import requests
import lxml.html
import os
import re
import urllib
import shutil
import nltk
import math
import collections
import time
import json
import bs4 as bs
import pandas as pd
import langdetect as lang
from nltk.corpus import stopwords
from datetime import datetime
from selenium import webdriver


class CollectPosts:

    def __init__(self, usr, pwd, url, id_start, id_end, sandbox):
        self.usr = usr
        self.pwd = pwd
        self.url = url
        self.id_start = id_start
        self.id_end = id_end
        self.sandbox = sandbox

    def login_session_groupsio(self):
        url = 'https://groups.io/login'
        session = requests.session()

        # get source code from login page
        login = session.get(url)
        login_html = lxml.html.fromstring(login.text)

        # store hidden field names and values in dictionary
        hidden_inputs = login_html.xpath(r'//form//input[@type="hidden"]')
        form = {x.attrib['name']: x.attrib['value'] for x in hidden_inputs}
        print(form)

        form['email'] = self.usr
        form['password'] = self.pwd

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Accept-Language': 'en-US,en;q=0.8,es;q=0.6',
                   'Connection': 'keep-alive'}

        response = session.post(url, data=form, headers=headers)

        # validate login response
        print('==========================================')
        print("URL:", response.url)
        print("Welcome", self.usr)
        print("Server response code:", response.status_code)
        print("Successful response:", response.ok)
        print('==========================================' + '\n')

        return session

    def login_session_yahoo(self, usr, pwd):
        url = 'https://login.yahoo.com'
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-popup-blocking")

        # open Chrome browser and go to login page
        browser = webdriver.Chrome(chrome_options=chrome_options)
        browser.get(url)

        # enter username and proceed to next step
        browser.find_element_by_id("login-username").send_keys(usr)
        browser.find_element_by_id("login-signin").click()

        time.sleep(1)

        # enter password and login
        browser.find_element_by_name("password").send_keys(pwd)
        browser.find_element_by_id("login-signin").click()

        return browser

    def groupsio(self, path_out):
        session = self.login_session_groupsio()

        for i in range(self.id_start, self.id_end+1):
            try:
                # [BeautifulSoup] parse html
                page = session.get(self.url + str(i))
                soup = bs.BeautifulSoup(page.text, 'html.parser')
                #print(soup.prettify())

                # format date
                timestamp = soup.find_all('font', class_='text-muted')[0].text.strip()
                timestamp = timestamp.replace("$('.timedisp').last().replaceWith(DisplayShortTime( ", "")
                timestamp = timestamp.replace(' , false,"America/New_York"));', "")
                date = datetime.fromtimestamp(int(timestamp[:10])).strftime('%Y-%m-%d %H:%M:%S')

                # format title
                title = soup.find_all('h4')[2]
                # if title contains dropdown menu button for hashtags
                if 'btn-xs' in str(title):
                    title_prefix = title.find('div', class_='hidden-sm').previousSibling.strip()
                    title_suffix = title.find_all('button')[0].text.strip()
                    title = title_prefix + " " + title_suffix
                else:
                    title = soup.find_all('h4')[2].text.strip()

                # format body
                body = soup.find_all('div', class_='forcebreak')[0]
                body = str(body).replace('<div class="forcebreak" dir="auto" style="white-space:pre-wrap;">', '')
                body = ''.join(str(body).rsplit('</div>', 1))

                # output
                if self.sandbox:
                    # print on screen
                    print(f"<id>{i}</id>")
                    print(f"<timestamp>{timestamp[:10]}</timestamp>")
                    print(f"<published>{date}</published>")
                    print(f"<title>{title}</title>")
                    print(f"<article>{body}</article>")
                else:
                    # write as text file
                    with open(path_out + str(f'{i:06}') + '.html', 'w', encoding='utf-8') as file:
                        print(f"<id>{i}</id>", file=file)
                        print(f"<timestamp>{timestamp[:10]}</timestamp>", file=file)
                        print(f"<published>{date}</published>", file=file)
                        print(f"<title>{title}</title>", file=file)
                        print(f"<article>{body}</article>", file=file)
                    # print counter on screen
                    print(str(i) + ' ...saved')

                # delay next request
                time.sleep(1)

            except Exception:
                with open(path_out + str(f'{i:06}') + ' EMPTY.html', 'w', encoding='utf-8') as file:
                    print('That message number does not exist. The message may have been deleted.', file=file)
                print(str(i) + '... EMPTY')
                pass

    def yahoogroups(self, path_out):
        browser = self.login_session_yahoo(self.usr, self.pwd)
        flag = False  # used for catching date format exceptions
        year = '2015'  # year of first post in specified range, used if year not explicit on first post

        for i in range(self.id_start, self.id_end):
            try:
                # browser.get(pathURL + str(i) + '.html')  # path for local cached file
                browser.get(self.url + str(i))
                page = browser.page_source
                soup = bs.BeautifulSoup(page, 'html.parser')
                # print(soup.prettify())

                # format date
                date = soup.find('span', class_='tip').text.strip()
                try:
                    timestamp = str(int(time.mktime(datetime.strptime(date, "%b %d, %Y").timetuple())))
                    year = datetime.fromtimestamp(int(timestamp[:10])).strftime('%Y')
                    if flag:
                        flag = False
                except Exception:
                    date = year + " " + date
                    timestamp = str(int(time.mktime(datetime.strptime(date, "%Y %b %d %H:%M %p").timetuple())))

                    if not self.sandbox:
                        # save exceptions into log file for further year verification
                        # Yahoo Groups has date format issues every time month falls in August regardless of year
                        if not flag:
                            with open(path_out + '_log.txt', 'a', encoding='utf-8') as file:
                                print('================================', file=file)
                                print(f'              {year}              ', file=file)
                                print('================================', file=file)
                            flag = True
                        with open(path_out + '_log.txt', 'a', encoding='utf-8') as file:
                            print(str(f'{i:06}'), file=file)
                date = datetime.fromtimestamp(int(timestamp[:10])).strftime('%Y-%m-%d %H:%M:%S')

                # format author
                author = soup.find('div', class_=re.compile("^author")).text.strip()

                # format title
                title = soup.find('h2', id='yg-msg-subject').text.strip()
                title = title.replace(str(i), '', 1)

                # format body
                # markup = soup.find('div', id=re.compile("^ygrps-yiv")) # uses "import re" for regex match
                markup = soup.find('div', class_='msg-content undoreset').contents[0]
                body = bs.BeautifulSoup(str(markup), 'html.parser')
                body.div.unwrap()

                # output
                if self.sandbox:
                    # print on screen
                    print(browser.current_url)
                    print(f"<id>{i}</id>")
                    print(f"<timestamp>{timestamp[:10]}</timestamp>")
                    print(f"<published>{date}</published>")
                    print(f"<author>{author}</author>")
                    print(f"<title>{title}</title>")
                    print(f"<article>{body}</article>")
                else:
                    # write as text file
                    with open(path_out + str(f'{i:06}') + '.html', 'w', encoding='utf-8') as file:
                        print(f"<id>{i}</id>", file=file)
                        print(f"<timestamp>{timestamp[:10]}</timestamp>", file=file)
                        print(f"<published>{date}</published>", file=file)
                        print(f"<author>{author}</author>", file=file)
                        print(f"<title>{title}</title>", file=file)
                        print(f"<article>{body}</article>", file=file)
                    # print counter on screen
                    print(str(i) + ' ...saved')

                    # delay next request
                    time.sleep(2)

            except Exception as e:
                with open(path_out + str(f'{i:06}') + ' EMPTY.html', 'w', encoding='utf-8') as file:
                    print('That message number does not exist. The message may have been deleted.', file=file)
                print(str(i) + '... EMPTY')
                print(e)
                pass

    def extract_images(self, path_in, path_out, path_root):
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36')]
        urllib.request.install_opener(opener)

        for i in range(self.id_start, self.id_end+1):
            i = str(i).zfill(6)

            if os.path.isfile(path_in + i + ".html"):
                try:
                    # try utf8 encoding first
                    soup = bs.BeautifulSoup(open(path_in + i + ".html", 'r', encoding='utf8'), 'lxml')
                except Exception as e:
                    soup = bs.BeautifulSoup(open(path_in + i + ".html", 'r'), 'lxml')

                images = soup.find_all('img')
                k = 1

                # if images tag found in html
                if re.search(r'src', str(images)):
                    print("\n")
                    print("=========================================================")
                    print(i + ": " + path_in + i + ".html")  # link to html file
                    print("=========================================================")

                    for image in images:
                        img = os.path.basename(image['src'])

                        for char in ["*", "?", "<", ">", ":", '"', "|", "/", "\\"]:
                            if char in img:
                                img = img.replace(char, '%')

                        if ".jpg" in img.lower():
                            img = re.compile('.jpg', re.IGNORECASE).split(img)[0] + ".jpg"
                            # img = img.split(".jpg", 1)[0] + ".jpg"
                        elif ".jpeg" in img.lower():
                            img = re.compile('.jpeg', re.IGNORECASE).split(img)[0] + ".jpeg"
                            # img = img.split(".jpeg", 1)[0] + ".jpeg"
                        elif ".gif" in img.lower():
                            img = re.compile('.gif', re.IGNORECASE).split(img)[0] + ".gif"
                            # img = img.split(".gif", 1)[0] + ".gif"
                        elif ".png" in img.lower():
                            img = re.compile('.png', re.IGNORECASE).split(img)[0] + ".png"
                            # img = img.split(".png", 1)[0] + ".png"
                        elif ".tiff" in img.lower():
                            img = re.compile('.tiff', re.IGNORECASE).split(img)[0] + ".tiff"
                            # img = img.split(".tiff", 1)[0] + ".tiff"
                        elif ".tif" in img.lower():
                            img = re.compile('.tif', re.IGNORECASE).split(img)[0] + ".tif"
                            # img = img.split(".tif", 1)[0] + ".tif"
                        elif ".bmp" in img.lower():
                            img = re.compile('.bmp', re.IGNORECASE).split(img)[0] + ".bmp"
                            # img = img.split(".bmp", 1)[0] + ".bmp"
                        else:
                            img = img + ".jpg"

                        print(path_out + i + "_" + img)
                        print(image['src'])

                        k += 1

                        # if test mode
                        if self.sandbox:
                            print("Test only")
                        else:
                            try:
                                urllib.request.urlretrieve(image['src'], path_out + i + "_" + img)

                                if not os.path.isfile(path_root + "_images.txt"):
                                    with open(path_root + "_images.txt", 'w', encoding='utf8') as file:
                                        print("POSTID\tSOURCE\tTARGET", file=file)

                                with open(path_root + "_images.txt", 'a', encoding='utf8') as file:
                                    print(i + "\t" + image['src'] + "\t" + img, file=file)

                            except Exception as e:
                                if not os.path.isfile(path_root + "_log_img.txt"):
                                    with open(path_root + "_log_img.txt", 'w', encoding='utf8') as file:
                                        print("POSTID\tERROR", file=file)

                                with open(path_root + "_log_img.txt", 'a', encoding='utf8') as file:
                                    print(i + "\t" + str(e), file=file)
                                print(e)
                else:
                    print(i + ": No images\n")

    def remove_html(self, path_in, path_out, get_author):
        author = ''
        with open(os.path.join(path_out, '_metadata.txt'), 'a', encoding='utf-8') as file:
            if get_author:
                print("POSTID\tTIMESTAMP\tDATE\tAUTHOR\tTITLE", file=file)
            else:
                print("POSTID\tTIMESTAMP\tDATE\t\tTITLE", file=file)

        for i in range(self.id_start, self.id_end+1):
            try:
                # [BeautifulSoup] parse html
                try:
                    # try UTF-8 encoding
                    soup = bs.BeautifulSoup(open(path_in + str(i).zfill(6) + '.html', 'r', encoding='UTF-8'), 'lxml')
                except Exception:
                    # process as non-specific enconding
                    soup = bs.BeautifulSoup(open(path_in + str(i).zfill(6) + '.html'), 'lxml')

                # format date
                timestamp = soup.find_all('timestamp')[0].text.strip()
                date = datetime.fromtimestamp(int(timestamp[:10])).strftime('%Y%m%d')

                # format title
                title = soup.find_all('title')[0].text.strip()
                title = title.replace('View All Topics', ' ')  # leftover from Groups.io
                title = title.replace('Mute', ' ')  # leftover from Groups.io
                title = re.sub('\s+', ' ', title)  # multiple spaces to single space
                title = title.strip()  # remove padding spaces
                title = title.replace('\t', ' ')  # tabs to spaces

                # format author
                if get_author:
                    author = soup.find_all('author')[0].text.strip()

                # format body
                body = soup.find_all('article')[0]
                body = str(body).replace('<br>', '\n')
                body = str(body).replace('<br/>', '\n')
                body = str(body).replace('<snip>', '')
                body = re.sub(r' +', ' ', str(body))
                body = bs.BeautifulSoup(body, 'lxml').find_all('article')[0].text.strip()

                # output
                if self.sandbox:
                    # print on screen
                    print(i)
                    print(date)
                    if get_author:
                        print(author)
                    print(title)
                    print(body)
                else:
                    # append to metadata file
                    with open(path_out + '_metadata.txt', 'a', encoding='utf-8') as file:
                        if get_author:
                            print(str(f'{i:06}') + '\t' + str(timestamp) + '\t' + str(date) + '\t' + author + '\t' + title, file=file)  # includes author
                        else:
                            print(str(f'{i:06}') + '\t' + str(timestamp) + '\t' + str(date) + '\t' + title, file=file)  # no author

                    with open(path_out + str(f'{i:06}') + '.txt', 'w', encoding='utf-8') as file:
                        print(body, file=file)

                    print(str(i) + ' ...saved')

            except Exception as e:
                with open(path_out + str(f'{i:06}') + ' EMPTY.txt', 'w', encoding='utf-8') as file:
                    print('That message number does not exist. The message may have been deleted.', file=file)
                    print(str(i) + ' ...ERROR: ' + str(e))
                pass


class FindDuplicates:

    def __init__(self, metadata_src, metadata_dst, corpus_src, corpus_dst, id_start, id_end):
        self.metadata_src = metadata_src
        self.metadata_dst = metadata_dst
        self.corpus_src = corpus_src
        self.corpus_dst = corpus_dst
        self.id_start = id_start
        self.id_end = id_end

    def vectorize(self, text):
        normalized = re.sub(r"\s+", ' ', text).lower().strip()
        normalized = re.sub(r"-", '', normalized)
        tokens = nltk.word_tokenize(normalized)
        ##enchanced processing
        # no_punctuation = [t for t in tokens if t not in string.punctuation]
        # no_stopwords = [w for w in no_punctuation if not w in stopwords.words('english')]
        # return collections.Counter(no_stopwords)
        return collections.Counter(tokens)

    def cosine_similarity(self, vector1, vector2):
        # calculates cosine similarity from two vectors
        intersection = set(vector1.keys()) & set(vector2.keys())
        numerator = sum([vector1[x] * vector2[x] for x in intersection])

        sum1 = sum([vector1[x]**2 for x in vector1.keys()])
        sum2 = sum([vector2[x]**2 for x in vector2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        similarity = 0.0 if not denominator else float(numerator) / denominator
        return similarity

    def compare_texts(self, cos_thresh, earliest_target_timestamp, docs_unique, docs_dups, docs_pending, corpus_unique, corpus_pending, research_terms, skipped_terms):
        # get source list of titles
        df1 = pd.read_csv(self.metadata_src, sep='\t', dtype=str, encoding='utf8')
        df1.set_index('POSTID', inplace=True)
        df1['TIMESTAMP'] = df1['TIMESTAMP'].astype(int)

        # get target list of titles
        df2 = pd.read_csv(self.metadata_dst, sep='\t', dtype=str, encoding='utf8')
        df2['TIMESTAMP'] = df2['TIMESTAMP'].astype(int)
        distance = 2 * 24 * 60 * 60  # days*hours*minutes*seconds time interval

        for i in range(self.id_start, self.id_end+1):
            i = str(f'{i:06}')

            try:
                timestamp1, date1, title1 = df1.loc[i]['TIMESTAMP'], df1.loc[i]['DATE'], df1.loc[i]['TITLE']
                # get target list of titles within timestamp interval
                compare = df2[['POSTID', 'TIMESTAMP', 'DATE', 'TITLE']][(df2['TIMESTAMP'] > timestamp1 - distance) & (df2['TIMESTAMP'] < timestamp1 + distance)]

                print('=' * 40 + '\nNEEDLE:\n' + '=' * 40 + f"\nPostID: {i} | CORPUS_1\nTitle: {title1}\n" + '=' * 40 + '\nHAYSTACK:\n' + '=' * 40)

                if any(term in title1.lower() for term in research_terms):
                    shutil.copyfile(f"{self.corpus_src}{i}.txt", f"{corpus_pending}{i}.txt")  # copy for further manual research

                    if not os.path.isfile(docs_pending):
                        with open(docs_pending, 'w', encoding='utf8') as f:
                            f.write("POSTID\tTIMESTAMP\tDATE\tTITLE\n")  # header

                    with open(docs_pending, 'a', encoding='utf8') as f:
                        f.write(f"{i}\t{timestamp1}\t{date1}\t{title1}\n")  # append

                elif any(term in title1.lower() for term in skipped_terms):
                    print('Document skipped')

                else:
                    matches = False

                    if timestamp1 > earliest_target_timestamp:

                        try:
                            # STEP 1: check if identical title exists in same date range
                            for k in range(int(compare.iloc[0]['POSTID']), int(compare.iloc[-1]['POSTID'])):
                                k = str(f'{k:06}')

                                try:
                                    title2 = compare['TITLE'][compare['POSTID'] == k].values[0]
                                    date2 = compare['DATE'][compare['POSTID'] == k].values[0]

                                    # if target title is contained in source title for same date (lowercase and spaces removed)
                                    if title2.lower().replace(' ', '') in title1.lower().replace(' ', '') and date2 == date1:
                                        matches = True
                                        print(f"Match found:\nPostID: {k} | CORPUS_2\nTitle: " + compare['TITLE'][compare['POSTID'] == k].values[0] + '\nDuplicate skipped\n\n')
                                        break  # exit loop if identical date and title found
                                except:
                                    pass

                            # STEP 2: if no title match found, check for document similarity
                            if not matches:
                                # check if identical title exists in same date rage
                                for k in range(int(compare.iloc[0]['POSTID']), int(compare.iloc[-1]['POSTID'])):
                                    k = str(f'{k:06}')

                                    # read source text file
                                    with open(f"{self.corpus_src}{i}.txt", 'r', encoding='utf8') as f:
                                        doc1 = f.read()
                                        doc1 = doc1.replace('>', '')  # remove email formatting (i.e., forward/quoted symbols)

                                    # read target text file for comparison
                                    try:
                                        with open(f"{self.corpus_dst}{k}.txt", 'r', encoding='utf8') as f:
                                            doc2 = f.read()
                                            doc2 = doc2.replace('>', '')
                                    except:
                                        doc2 = ''
                                        pass

                                    cos = self.cosine_similarity(self.vectorize(doc1), self.vectorize(doc2))

                                    if cos > cos_thresh:
                                        matches = True
                                        print(f"Match found:\nPostID: {k} | CORPUS_2")
                                        try:
                                            print('Title: ' + compare['TITLE'][compare['POSTID'] == k].values[0])
                                        except:
                                            print('Error: Cannot read title')
                                        print(f"Cosine Similarity: {cos}")
                                        print(self.vectorize(doc1))
                                        print(self.vectorize(doc2))
                                        print('Duplicate skipped\n\n')
                                        # print('\n\n' + '=' * 40 + 'NEEDLE:' + '=' * 40 + '\n' + doc1)  # print full document texts
                                        # print('\n\n' + '=' * 40 + 'HAYSTACK:' + '=' * 40 + '\n' + doc2)
                                        break

                        except Exception as e:
                            print(f"Error: {e}\n\n")

                    # if no duplicates were found via identical title or document similarity
                    if not matches:
                        shutil.copyfile(f"{self.corpus_src}{i}.txt", f"{corpus_unique}{i}.txt")
                        print("No duplicates found. File copied to unique selection.\n\n")

                        if not os.path.isfile(docs_unique):
                            with open(docs_unique, 'w', encoding='utf8') as f:
                                f.write('POSTID\tTIMESTAMP\tDATE\tTITLE\n')

                        with open(docs_unique, 'a', encoding='utf8') as f:
                            f.write(f"{i}\t{timestamp1}\t{date1}\t{title1}\n")  # append
                    else:
                        if not os.path.isfile(docs_dups):
                            with open(docs_dups, 'w', encoding='utf8') as f:
                                f.write("CORPUS_1\tCORPUS_2\n")

                        with open(docs_dups, 'a', encoding='utf8') as f:
                            f.write(f"{i}\t{k}\n")  # append
            except:
                pass


class Utilities:

    def __init__(self, path_in, path_out):
        self.path_in = path_in
        self.path_out = path_out

    def split_multi_article(self):
        articles = [article for article in os.listdir(self.path_in) if article.endswith('.txt')]

        for article in articles:
            with open(os.path.join(self.path_in, article), 'r') as f:
                text = f.read()

                # split digest messages according to each individual split convention
                items = [item for item in text.split('**********  GAIN  **********')]
                if len(items) < 3:
                    items = [item for item in text.split('****************************************************************')]
                if len(items) < 3:
                    items = [item for item in text.split('---------------------------------------------------------------------')]
                if len(items) < 3:
                    items = [item for item in text.split('----------------------------------------------------------------')]
                if len(items) < 3:
                    items = [item for item in text.split('>>>--------------------------->>>')]

                for i, item in enumerate(items):
                    with open(os.path.join(self.path_out, article[:-4] + '_' + str(i).zfill(2) + '.txt'), 'w') as f:
                        f.write(item)

                    print(item)

    def clean_text(self):
        # only used for cleaning corpus 3
        articles = [article for article in os.listdir(self.path_in) if article.endswith('.txt')]

        for article in articles:
            with open(os.path.join(self.path_in, article), 'r') as f:
                txt = f.readlines()
                if txt[0].strip().startswith('ITEM'):
                    txt.pop(0)
                elif len(txt[0].strip()) == 0:
                    txt.pop(0)
                elif re.search(r'^[0-9]+\.$', txt[0].strip()):
                    txt.pop(0)
                for i, _ in enumerate(txt):
                    txt[i] = txt[i].replace('<<<---------------------------<<<', '')
                    txt[i] = txt[i].replace('_______________________________________________', '')
                    txt[i] = txt[i].replace('>>>', '')
                    txt[i] = txt[i].strip() + '\n'

                print(txt)

            with open(os.path.join(self.path_in, article), 'w') as f:
                f.writelines(txt)

    def remove_signature_text(self, cut_points_list):
        articles = [article for article in os.listdir(self.path_in) if article.endswith('.txt')]

        for article in articles:
            print('Removing signature from article:', article)

            cut = False
            with open(os.path.join(self.path_in, article), 'r', encoding='utf-8') as f:
                txt = f.readlines()
                i = len(txt)
                for i, _ in enumerate(txt):
                    # list must be converted to tuple for testing multiple conditions
                    if txt[i].strip().startswith(tuple(cut_points_list)):
                        cut = True
                        break
                if cut:
                    txt = txt[:i]  # keep text up to the cut point

            with open(os.path.join(self.path_in, article), 'w', encoding='utf-8') as f:
                f.writelines(txt)

    def replace_substr(self, old_substr, new_substr):
        articles = [article for article in os.listdir(self.path_in) if article.endswith('.txt')]

        for article in articles:
            print('Substring replacement on article:', article)

            with open(os.path.join(self.path_in, article), 'r', encoding='utf-8') as f:
                txt = f.read()
                txt = re.sub(old_substr, new_substr, txt)

            with open(os.path.join(self.path_in, article), 'w', encoding='utf-8') as f:
                f.writelines(txt)

    def date_to_timestamp(self, date):
        timestamp = ''

        try:
            timestamp = str(int(time.mktime(datetime.strptime(date, "%b %d, %Y").timetuple())))
        except:
            try:
                timestamp = str(int(time.mktime(datetime.strptime(date, "%b %d %Y").timetuple())))
            except:
                try:
                    timestamp = str(int(time.mktime(datetime.strptime(date, "%b. %d, %Y").timetuple())))
                except:
                    try:
                        timestamp = str(int(time.mktime(datetime.strptime(date, "%bt. %d, %Y").timetuple())))
                    except:
                        try:
                            timestamp = str(int(time.mktime(datetime.strptime(date, "%B %d, %Y").timetuple())))
                        except:
                            try:
                                timestamp = str(int(time.mktime(datetime.strptime(date, "%B %d , %Y").timetuple())))
                            except:
                                try:
                                    timestamp = str(int(time.mktime(datetime.strptime(date, "%B %d %Y").timetuple())))
                                except:
                                    try:
                                        timestamp = str(int(time.mktime(datetime.strptime(date, "%d %B, %Y").timetuple())))
                                    except:
                                        try:
                                            timestamp = str(int(time.mktime(datetime.strptime(date, "%d %B %Y").timetuple())))
                                        except:
                                            try:
                                                timestamp = str(int(time.mktime(datetime.strptime(date, "%dth %B %Y").timetuple())))
                                            except:
                                                try:
                                                    timestamp = str(int(time.mktime(datetime.strptime(date, "%d %b %Y").timetuple())))
                                                except:
                                                    try:
                                                        timestamp = str(int(time.mktime(datetime.strptime(date, "%m/%d/%y").timetuple())))
                                                    except:
                                                        try:
                                                            timestamp = str(int(time.mktime(datetime.strptime(date, "%m/%d/%y %M:%S %p").timetuple())))
                                                        except:
                                                            try:
                                                                timestamp = str(int(time.mktime(datetime.strptime(date, "%b/%d/%y %I:%M %p").timetuple())))
                                                            except:
                                                                try:
                                                                    timestamp = str(int(time.mktime(datetime.strptime(date, "%B %d, %Y, %A").timetuple())))
                                                                except:
                                                                    try:
                                                                        timestamp = str(int(time.mktime(datetime.strptime(date, "%Y-%m-%d").timetuple())))
                                                                    except:
                                                                        pass
        if timestamp == '':
            try:
                timestamp = str(int(time.mktime(datetime.strptime(date, "%A, %B %d, %Y").timetuple())))
            except:
                try:
                    timestamp = str(int(time.mktime(datetime.strptime(date, "%A, %B %d, %Y").timetuple())))
                except:
                    try:
                        timestamp = str(int(time.mktime(datetime.strptime(date, "%A, %B %d, %Y").timetuple())))
                    except:
                        try:
                            timestamp = str(int(time.mktime(datetime.strptime(date, "%a, %d %b %Y").timetuple())))
                        except:
                            try:
                                timestamp = str(int(time.mktime(datetime.strptime(date, "%A %B %d, %Y").timetuple())))
                            except:
                                try:
                                    timestamp = str(int(time.mktime(datetime.strptime(date, "%m/%d/%y %H:%M").timetuple())))
                                except:
                                    try:
                                        timestamp = str(int(time.mktime(datetime.strptime(date, "%m/%d/%Y").timetuple())))
                                    except:
                                        try:
                                            timestamp = str(int(time.mktime(datetime.strptime(date, "%B %d,%Y").timetuple())))
                                        except:
                                            try:
                                                timestamp = str(int(time.mktime(datetime.strptime(date, "%A %dth %b, %Y").timetuple())))
                                            except:
                                                try:
                                                    timestamp = str(int(time.mktime(datetime.strptime(date, "%A %dth %B, %Y").timetuple())))
                                                except:
                                                    try:
                                                        timestamp = str(int(time.mktime(datetime.strptime(date, "%a, %d %b %Y").timetuple())))
                                                    except:
                                                        try:
                                                            timestamp = str(int(time.mktime(datetime.strptime(date, "%a %d %b, %Y").timetuple())))
                                                        except:
                                                            try:
                                                                timestamp = str(int(time.mktime(datetime.strptime(date, "%a %dth %b, %Y").timetuple())))
                                                            except:
                                                                try:
                                                                    timestamp = str(int(time.mktime(datetime.strptime(date, "%a %dth %B, %Y").timetuple())))
                                                                except:
                                                                    try:
                                                                        timestamp = str(int(time.mktime(datetime.strptime(date, "%a, %d %b %Y %H:%M:%S").timetuple())))
                                                                    except:
                                                                        try:
                                                                            timestamp = str(int(time.mktime(datetime.strptime(date, "%a, %d %B, %Y").timetuple())))
                                                                        except:
                                                                            pass


        return timestamp

    def get_metadata_corpus_3(self, path_out):
        articles = [article for article in os.listdir(self.path_in) if article.endswith('.txt')]
        #df = pd.DataFrame(columns=['POSTID', 'TIMESTAMP', 'DATE', 'LOCATION', 'TITLE', 'AUTHOR', 'URL', 'SOURCE'])
        df = pd.DataFrame(columns=['POSTID', 'TIMESTAMP', 'DATE', 'LOCATION', 'TITLE'])

        #for article in articles[-2:-1]:
        for article in articles:
            id = article.replace('.txt', '')
            source, author, url, date, timestamp, location, title = '', '', '', '', '', '', ''

            with open(os.path.join(self.path_in, article), 'r') as f:
                txt = f.readlines()

            for i, _ in enumerate(txt):
                if txt[i].lower().startswith('source:'):
                    source = txt[i][len('source:'):].strip()
                    print(source)
                elif txt[i].lower().startswith('author:'):
                    author = txt[i][len('author:'):].strip()
                    print(author)
                elif txt[i].lower().startswith('url:'):
                    url = txt[i][len('url:'):].strip()
                    print(url)
                elif txt[i].lower().startswith('date:'):
                    date = txt[i][len('date:'):].strip()
                    timestamp = self.date_to_timestamp(date)
                    if timestamp != '':
                        date = datetime.fromtimestamp(int(timestamp[:10])).strftime('%Y%m%d')
                    print(date, timestamp)
                elif txt[i].lower().startswith('location:'):
                    location = txt[i][len('location:'):].strip()
                    print(location)
                elif txt[i].lower().startswith('title:'):
                    title = txt[i][len('title:'):].strip()
                    print(title)
                elif txt[i].lower().startswith('news:'):
                    title = txt[i][len('news:'):].strip()
                    print(title)
                elif txt[i].lower().startswith('editorial:'):
                    title = txt[i][len('editorial:'):].strip()
                    print(title)

            #df = df.append(pd.DataFrame([[id, timestamp, date, '[' + location + ']', title, author, url, source]], columns=['POSTID', 'TIMESTAMP', 'DATE', 'LOCATION', 'TITLE', 'AUTHOR', 'URL', 'SOURCE']))
            df = df.append(pd.DataFrame([[id, timestamp, date, '[' + location + ']', title]], columns=['POSTID', 'TIMESTAMP', 'DATE', 'LOCATION', 'TITLE']))

        df = df.reset_index(drop=True)
        df.to_csv(os.path.join(path_out), sep='\t', index=None)

    def detect_language(self, path_out):
        articles = [article for article in os.listdir(self.path_in) if article.endswith('.txt')]
        df = pd.DataFrame(columns=['POSTID', 'LANG'])

        for article in articles:
            try:
                with open(os.path.join(self.path_in, article), 'r') as f:
                    txt = f.read()
            except:
                with open(os.path.join(self.path_in, article), 'r', encoding='utf-8') as f:
                    txt = f.read()

            try:
                language = lang.detect(txt)
            except:
                language = ''

            id = article.split('.')[0]
            df = df.append(pd.DataFrame([[id, language]], columns=['POSTID', 'LANG']))
            print(id, '--->', language)

        df = df.reset_index(drop=True)
        df.to_csv(path_out, sep='\t', index=None)


########################################### PROCESS POSTS FROM CORPORA 1 AND 2 #####################################

# Collect posts from Yahoo Groups
scrape_yahoo = CollectPosts(os.environ['YAHOO_GROUPS_USR'], os.environ['YAHOO_GROUPS_PWD'], os.environ['YAHOO_GROUPS_URL'], id_start=1, id_end=116102, sandbox=False)
scrape_yahoo.yahoogroups(path_out='D:/Data/corpus_1/html/')

# Collect posts from Groups.IO
scrape_groupsio = CollectPosts(os.environ['GROUPSIO_USR'], os.environ['GROUPSIO_PWD'], os.environ['GROUPSIO_URL'], id_start=1, id_end=131487, sandbox=False)
scrape_groupsio.groupsio(path_out='D:/Data/corpus_2/html/')
scrape_groupsio.extract_images(path_in='D:/Data/corpus_2/html/', path_out='D:/Data/corpus_2/img/', path_root='D:/Data/corpus_2/')
scrape_groupsio.remove_html(path_in='D:/Data/corpus_2/html/', path_out='D:/Data/corpus_2/txt/', get_author=False)

# Create text analysis object. Used for getting cosine similarity of compared files (i.e., i=4145 and k=126 are almost identical)
analyze_text = FindDuplicates(metadata_src="D:/Data/corpus_1/metadata.txt",
                              metadata_dst="D:/Data/corpus_2/metadata.txt",
                              corpus_src="D:/Data/corpus_1/txt/",
                              corpus_dst="D:/Data/corpus_2/txt/",
                              id_start=1,
                              id_end=116101)

# Cosine similarity threshold, empirical suggested value = 0.94
# The earliest target timestamp is from the first known post date in the target corpus for comparison
analyze_text.compare_texts(cos_thresh=0.94,
                           earliest_target_timestamp=1016057981,
                           docs_unique="D:/Data/corpus_1/_metadata_unique_secondpass.txt",
                           docs_dups="D:/Data/corpus_1/_metadata_duplicates_secondpass.txt",
                           docs_pending="D:/Data/corpus_1/_metadata_gain_digest_secondpass.txt",
                           corpus_unique="D:/Data/corpus_1/unique/",
                           corpus_pending="D:/Data/corpus_1/gain_digest/",
                           research_terms=['gain digest'],
                           skipped_terms=['group announcement','file uploaded','tnuk digest','tnuk-digest','tnukdigest','transgendernews'])


################################################## CLEAN ARTICLES TEXT ##################################################

# list of signatures is not exhaustive and may need further exploration
cut_points = ['Kindly appreciate that Brenda',
              "Moderator's Note: Thanks to Brenda",
              'UKPFC-NEWS is operated by Press for Change',
              'This message comes to you from Press for Change',
              'Download Yahoo! Messenger now',
              '------------------------ Yahoo! Groups Sponsor',
              'Do You Yahoo',
              'Gesendet von Yahoo'
              ]

# corpus 1
articles = Utilities(path_in="D:/Data/corpus_1/unique", path_out="")
articles.replace_substr(old_substr='^> |^>|\n> |\n>', new_substr='\n')  # remove chevron at beginning of each line
articles.remove_signature_text(cut_points)  # cut newsgroup signature text from bottom of articles

# corpus 2
articles = Utilities(path_in="D:/Data/corpus_2/txt", path_out="")
articles.replace_substr(old_substr='^> |^>|\n> |\n>', new_substr='\n')  # remove chevron at beginning of each line
articles.remove_signature_text(cut_points)  # cut newsgroup signature text from bottom of articles

# corpus 3
articles = Utilities(path_in="D:/Data/corpus_3/unique_2", path_out="")
articles.replace_substr(old_substr='^> |^>|\n> |\n>', new_substr='\n')  # remove chevron at beginning of each line
articles.remove_signature_text(cut_points)  # cut newsgroup signature text from bottom of articles


########################################### PROCESS POSTS FROM CORPUS 3 ###############################################

# split posts containing multiple articles digest-style
split = Utilities(path_in="D:/Data/corpus_1/gain_digest", path_out="D:/Data/corpus_3/txt")
split.split_multi_article()

# 'articles" object
articles = Utilities(path_in="D:/Data/corpus_3/txt", path_out="")

# clean posts
articles.clean_text()  # run twice to remove first lines that have dividers or contain only a number

# make archive copy of posts and rename originals (non-destructive approach to digest-style posts)
files = [file for file in os.listdir("D:/Data/corpus_3/txt") if file.endswith('.txt')]
os.makedirs("D:/Data/corpus_3/txt_archive")
for file in files:
    shutil.copyfile(os.path.join("D:/Data/corpus_3/txt", file), os.path.join("D:/Data/corpus_3/txt_archive", file))
for i, file in enumerate(files, start=1):
    os.rename(os.path.join("D:/Data/corpus_3/txt", file), os.path.join("D:/Data/corpus_3/txt", str(i).zfill(6) + '.txt'))

# extract metadata from corpus 3 articles and save to metadata file (depends on article text format)
articles.get_metadata_corpus_3("D:/Data/corpus_3/metadata.txt")

# cut newsgroup signature text from bottom of article
articles.remove_signature_text('Thank you for subscribing to')

# Create object for cosine similarity comparison Corpus 3 vs Corpus 1 -----------------------------------
analyze_text_corpus_3_a = FindDuplicates(metadata_src="D:/Data/corpus_3/metadata.txt",
                                       metadata_dst="D:/Data/corpus_1/metadata_unique.txt",
                                       corpus_src="D:/Data/corpus_3/txt/",
                                       corpus_dst="D:/Data/corpus_1/txt/",
                                       id_start=1,
                                       id_end=474)

# Cosine similarity threshold, empirical suggested value = 0.94
# The earliest target timestamp is from the first known post date in the target corpus for comparison
analyze_text_corpus_3_a.compare_texts(cos_thresh=0.94,
                                    earliest_target_timestamp=965700480,
                                    docs_unique="D:/Data/corpus_3/metadata_unique_1.txt",
                                    docs_dups="D:/Data/corpus_3/metadata_duplicates_1.txt",
                                    docs_pending="",
                                    corpus_unique="D:/Data/corpus_3/unique_1/",
                                    corpus_pending="",
                                    research_terms=[],
                                    skipped_terms=[])

# Create object for cosine similarity comparison Corpus 3 vs Corpus 2 -----------------------------------
analyze_text_corpus_3_b = FindDuplicates(metadata_src="D:/Data/corpus_3/metadata_unique_1.txt",
                                       metadata_dst="D:/Data/corpus_2/metadata.txt",
                                       corpus_src="D:/Data/corpus_3/txt/",
                                       corpus_dst="D:/Data/corpus_2/txt/",
                                       id_start=1,
                                       id_end=474)

# Cosine similarity threshold, empirical suggested value = 0.94
# The earliest target timestamp is from the first known post date in the target corpus for comparison
analyze_text_corpus_3_b.compare_texts(cos_thresh=0.94,
                                    earliest_target_timestamp=1016057981,
                                    docs_unique="D:/Data/corpus_3/metadata_unique_2.txt",
                                    docs_dups="D:/Data/corpus_3/metadata_duplicates_2.txt",
                                    docs_pending="",
                                    corpus_unique="D:/Data/corpus_3/unique_2/",
                                    corpus_pending="",
                                    research_terms=[],
                                    skipped_terms=[])


########################################### COMBINE ALL UNIQUE DOCS INTO SINGLE CORPUS ##########################################

df_corpus_1 = pd.read_csv("D:/Data/corpus_1/metadata_unique.txt", sep='\t', dtype=str)
df_corpus_2 = pd.read_csv("D:/Data/corpus_2/metadata.txt", sep='\t', dtype=str)
df_corpus_3 = pd.read_csv("D:/Data/corpus_3/metadata_unique_2.txt", sep='\t', dtype=str)

df_corpus_1['CORPUS'] = 'corpus_1'
df_corpus_2['CORPUS'] = 'corpus_2'
df_corpus_3['CORPUS'] = 'corpus_3'

df_corpus = pd.concat([df_corpus_1, df_corpus_2, df_corpus_3], ignore_index=True)
df_corpus['LOCATION'] = ''
df_corpus['TYPE'] = ''

df_corpus = df_corpus[['CORPUS', 'POSTID', 'TIMESTAMP', 'DATE', 'TITLE', 'LOCATION', 'TYPE']]


########################################### CLEAN METADATA #####################################################################

temp_type = []
temp_location = []
temp_source = []

#for i, row in df_corpus[9000:10000].iterrows():
for i, row in df_corpus.iterrows():
    doc_type, doc_location, doc_source = '', '', ''
    doc_type_raw, doc_location_raw, doc_source_raw = '', '', ''

    title_raw = row['TITLE'].replace(']]', ']')

    if re.search(r'^\[', title_raw.strip()):
        try:
            doc_type_raw = title_raw.split(']')[0] + ']'
            doc_type = title_raw.split(']')[0].replace('[', '').strip()
            doc_location_raw = title_raw.split(']')[1] + ']'
            doc_location = title_raw.split(']')[1].replace('[', '').strip()
        except:
            try:
                doc_type_raw = title_raw.split('}')[0] + ']'
                doc_type = title_raw.split('}')[0].replace('[', '').strip()
                doc_location_raw = title_raw.split('}')[1] + '}'
                doc_location = title_raw.split('}')[1].replace('[', '').strip()
            except:
                pass

    if re.search(r'\]$', title_raw.strip()):
        doc_source_raw = '[' + title_raw.split('[')[-1]
        doc_source = title_raw.split('[')[-1].replace(']', '').strip()

        if len(doc_source_raw) == len(title_raw) + 1:
            doc_source_raw = '{' + title_raw.split('{')[-1]
            doc_source = title_raw.split('{')[-1].replace(']', '').strip()


    doc_title = title_raw.replace(doc_type_raw, '').replace(doc_location_raw, '').replace(doc_source_raw, '')
    doc_title = doc_title.replace('[]', '').replace('{}', '').strip()

    # no location and/or source info exists within delimiters
    if doc_location == doc_title:
        doc_location = ''
    if doc_source == doc_title:
        doc_source = ''

    print(i)
    print('Raw:', row['TITLE'])
    print('Typ:', doc_type)
    print('Loc:', doc_location)
    print('Src:', doc_source)
    print('Ttl:', doc_title)
    print('=' * 20)

    if doc_type != '':
        temp_type.append(doc_type.upper())
    if doc_location != '':
        temp_location.append(doc_location.upper())
    if doc_source != '':
        temp_source.append(doc_source.upper())

# lists of unique sorted terms, raw
temp_type_raw = sorted(list(set(temp_type)))
temp_location_raw = sorted(list(set(temp_location)))
temp_source_raw = sorted(list(set(temp_source)))

len(temp_type_raw)
len(temp_location_raw)
len(temp_source_raw)

# prepare lists of stopwords, month names, US states (used in cleaning process)
stop_words = [term.upper() for term in stopwords.words('english')]
stop_words.extend(['RE','FW'])
months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
states = json.load(open("D:/Data/corpus_common/states.json"))

# lists of unique sorted terms, clean

temp_type_clean = ' '.join(temp_type_raw)
temp_type_clean = re.sub(r'[^A-Z]', ' ', temp_type_clean)
temp_type_clean = re.sub(r'\s+', ' ', temp_type_clean).strip()
temp_type_clean = sorted(list(set(temp_type_clean.split(' '))))
temp_type_clean = [item for item in temp_type_clean if item not in stop_words]

temp_location_clean = ' '.join(temp_location_raw)
temp_location_clean = re.sub(r'[^A-Z]', ' ', temp_location_clean)
temp_location_clean = re.sub(r'\s+', ' ', temp_location_clean).strip()
temp_location_clean = sorted(list(set(temp_location_clean.split(' '))))
temp_location_clean = [item for item in temp_location_clean if item not in stop_words]

temp_source_clean = []
for item in temp_source_raw:
    item = re.sub(r'[^A-Z\.\:]', ' ', item)
    item = re.sub(r'\s+', ' ', item).strip()
    if item.split(' ')[-1] in months:
        item = ''.join(item[:-1])
    temp_source_clean.append(item)
    temp_source_clean = sorted(list(set(temp_source_clean)))


# make temp lists for manual labeling
manual_labels_1 = [item for item in temp_type_clean if item not in states.keys() if len(item) > 1]
manual_labels_1 = [item for item in manual_labels_1 if item not in states.values()]
manual_labels_2 = [item for item in temp_location_clean if item not in states.keys() if len(item) > 1]
manual_labels_2 = [item for item in manual_labels_2 if item not in states.values()]

# combine temp manual labeling lists into single sorted list with no duplicates
manual_labels = sorted(list(set(manual_labels_1 + manual_labels_2)))

# write two list copies as JSON files for manual labeling (places and article types)
filenames = ['labels_places.json','labels_types.json']
for filename in filenames:
    with open(f"D:/Data/corpus_common/{filename}", 'w') as f:
        # start JSON object
        f.write('{\n')
        # write all items, line by line, except last item in list (these end with comma, last one doesn't)
        for item in manual_labels[:-1]:
            f.write(f' "{item}": "",\n')
        f.write(f' "{manual_labels[-1]}": ""\n')
        # close JSON object
        f.write('}')


# After lists has been saved to disk, manually edit each file as follows:

# 1. Edit list of Places
# remove 'article type' terms from 'places' list (manually)
# add curated dictionary value to each JSON key (manually)
# load manually edited file (load below):
labels_places = json.load(open("D:/Data/corpus_common/labels_places.json"))

# 2. Edit list of Article Types
# remove 'place' terms from 'article types' list (compare dictionaries):
labels_types = json.load(open("D:/Data/corpus_common/labels_types.json"))
labels_types = {k : labels_types[k] for k in set(labels_types) - set(labels_places)}
labels_types = {k : labels_types[k] for k in sorted(labels_types.keys())}

with open("D:/Data/corpus_common/labels_types.json", 'w') as j:
    json.dump(labels_types, j, indent=1)



################################### DETECT AND TAG ARTICLES BY PLACE AND TYPE ###############################################################

# load manually-edited labels files
labels_places = json.load(open("D:/Data/corpus_common/labels_places.json"))
labels_types = json.load(open("D:/Data/corpus_common/labels_types.json"))


for i, row in df_corpus.iterrows():
    title_tokens_raw = row['TITLE']
    title_tokens_clean = re.sub(r'[^A-Z ]', '', title_tokens_raw.upper()).split(' ')
    title_tokens_clean = [term for term in title_tokens_clean if term not in stop_words
                                                                and term != '' and len(term) > 1]
    # extract tags from titles
    tags_places, tags_types = [], []
    for token in title_tokens_clean:
        if token in labels_places:
            tags_places.append(labels_places[token])
        if token in labels_types:
            tags_types.append(labels_types[token])
    tags_places = '|'.join(list(set(tags_places)))
    tags_types = '|'.join(list(set(tags_types)))

    # update corpus
    if len(tags_places) > 0:
        df_corpus.loc[i, 'LOCATION'] = tags_places
    if len(tags_types) > 0:
        df_corpus.loc[i, 'TYPE'] = tags_types

    print(i, tags_places, tags_types)

# save tagged metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


########################################### DETECT LOCATION ARTICLES IN CORPUS 3 #################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# read location metadata from corpus 3 and update df_corpus

df_location = pd.read_csv("D:/Data/corpus_3/metadata.txt", sep='\t', dtype=str, usecols=['POSTID','LOCATION'])

rows_update = [(i, row['POSTID']) for i, row in df_corpus[df_corpus['CORPUS'] == 'corpus_3'].iterrows()]

for i, postid in rows_update:
    updated_location = df_location[df_location['POSTID'] == postid]['LOCATION'].iloc[0].upper()
    updated_location = re.sub(r'[^A-Z, \|]', '', updated_location)
    updated_location = updated_location.replace(', ', ',')
    # normalize US to USA, part 1
    if updated_location == 'US':
        updated_location = 'USA'
    print(postid, df_corpus.loc[i, 'LOCATION'], '--->', updated_location)
    df_corpus.loc[i, 'LOCATION'] = updated_location

# save updated metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


############################################### NORMALIZE LOCATION FOR USA ######################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# normalize US to USA, part 2 (USA only country in data labeled with states), remove duplicate instances (i.e. 'USA|WV,USA')

df_corpus['LOCATION'] = df_corpus['LOCATION'].str.replace(',US',',USA')
df_corpus['LOCATION'] = df_corpus['LOCATION'].str.replace(',USA\|USA',',USA')

for i, row in df_corpus.iterrows():
    if re.search(r'USA\|[A-Z]{2},USA', row['LOCATION']):
        # remove duplicated 'USA|' where not preceeded by comma
        updated_location = re.sub('(?<!,)USA\|', '', row['LOCATION'])
        df_corpus.loc[i, 'LOCATION'] = updated_location
        print(i, updated_location)

# save updated metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


##################################################### CLEAN TITLES ########################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# new column for clean titles
df_corpus['TITLE_CLEAN'] = ''

# colons must not be preceeded by space
df_corpus['TITLE'] = df_corpus['TITLE'].str.replace(' :', ':')

# clean titles
for i, row in df_corpus.iterrows():
    title = row['TITLE']

    # replace curly brackets with square brackets
    title = title.replace('{', '[').replace('}', ']')

    # remove everything between brackets, inclusive
    if title.count('[') == title.count(']'):
        while title.count('[') > 0 and title.count(']') > 0:
            title = title.replace(title[title.find('['):title.find(']')+1], '').strip()

    # replace misc terms (preferred over Series.str.replace to keep it case insensitive)
    replace_terms = ['FWD:','FWD ','RE:','FW:','RE ','FW ',
                     'ESP:','ITA:','FRA:','POR:','DEU:','SVE:'
                     'AUS:','USA:','US:','UK:','CAN:','GB:','EN:','ES:','ESO']
    for replace_term in replace_terms:
        title = re.sub(replace_term, '', title, flags=re.IGNORECASE).strip()

    # older articles follow convention for place/language specified before dash at title beginning
    # set max distance from start to 20 to minimize false positives (i.e. dash in middle of article hyphenates words)
    break_point = title.find('-')
    if 20 > break_point > 0:
        title = title[break_point+1:].strip()

    # title must start with alphanumeric character, quotes or opening question or exclamation mark (for spanish)
    while re.match(r'^[^A-Za-z0-9\'"¿¡]', title):
        title = re.sub(r'^[^A-Za-z0-9\'"¿¡]', ' ', title).strip()

    # remove multiple spaces and ellipses
    title = re.sub(r'\.{3}', ' ', title).strip()
    title = re.sub(r'\s{2,}', ' ', title).strip()

    print(row['CORPUS'], row['POSTID'], title)

    df_corpus.loc[i, 'TITLE_CLEAN'] = title

# save updated metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


##################################################### LANGUAGE DETECTION ########################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# corpus 1
articles = Utilities(path_in="D:/Data/corpus_1/unique", path_out="")
articles.detect_language("D:/Data/corpus_1/metadata_language.txt")

# corpus 2
articles = Utilities(path_in="D:/Data/corpus_2/txt", path_out="")
articles.detect_language("D:/Data/corpus_2/metadata_language.txt")

# corpus 3
articles = Utilities(path_in="D:/Data/corpus_3/unique_2", path_out="")
articles.detect_language("D:/Data/corpus_3/metadata_language.txt")

# update language for corpus 1
lang_file = pd.read_csv("D:/Data/corpus_1/metadata_language.txt", sep='\t', dtype=str)
df_corpus_1 = df_corpus[df_corpus['CORPUS'] == 'corpus_1'].merge(lang_file, how='left', on='POSTID')

# update language for corpus 2
lang_file = pd.read_csv("D:/Data/corpus_2/metadata_language.txt", sep='\t', dtype=str)
df_corpus_2 = df_corpus[df_corpus['CORPUS'] == 'corpus_2'].merge(lang_file, how='left', on='POSTID')

# update language for corpus 3
lang_file = pd.read_csv("D:/Data/corpus_3/metadata_language.txt", sep='\t', dtype=str)
df_corpus_3 = df_corpus[df_corpus['CORPUS'] == 'corpus_3'].merge(lang_file, how='left', on='POSTID')

# concatenate df's
df_corpus = pd.concat([df_corpus_1, df_corpus_2, df_corpus_3], ignore_index=True)

# save updated metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


##################################################### EXTRACT URLS ###########################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# new URLS column
df_corpus['URLS'] = ''

# loop through articles
for i, row in df_corpus.iterrows():
    if row['CORPUS'] == 'corpus_1':
        path_article = "D:/Data/corpus_1/unique/"
    elif row['CORPUS'] == 'corpus_2':
        path_article = "D:/Data/corpus_2/txt/"
    elif row['CORPUS'] == 'corpus_3':
        path_article = "D:/Data/corpus_3/unique_2/"

    print('Extracting URLS from corpus/article:', row['CORPUS'], '/', row['POSTID'])

    try:
        with open(f"{path_article}{row['POSTID']}.txt", 'r', encoding='utf-8') as f:
            txt = f.read()

        needles = ['SOURCE:','AUTHOR:','URL:','DATE:','ITEM:','SUBJECT:','LOCATION:','TITLE:','TINYURL:','VIA:','FROM:','PHOTO:','PUBLISHED']
        for needle in needles:
            txt = re.sub(needle, '\n\n', txt, flags=re.IGNORECASE)

        txt = re.sub(r'www.', 'http://www.', txt, flags=re.IGNORECASE)  # format if no http and only www present
        txt = re.sub(r'http://http://www.', 'http://www.', txt, flags=re.IGNORECASE)  # reconfigure http part
        txt = re.sub(r'http', ' http', txt)  # ensure http is not connected to any previous text

        txt = re.sub(r'[-=#.*+~_]{7,}', ' ', txt, flags=re.IGNORECASE)  # replace line dividers
        txt = txt.replace('(', ' ').replace(')', ' ').replace('[', ' ').replace(']', ' ').replace('<', ' ').replace('>', ' ')
        txt = txt.replace('\n\n', ' ').replace('\n', '')

        txt = re.sub(r'.html', '.html ', txt, flags=re.IGNORECASE)
        txt = re.sub(r'.html \?', '.html?', txt, flags=re.IGNORECASE)
        txt = re.sub(r'.html &', '.html&', txt, flags=re.IGNORECASE)

        urls = re.findall(r'http[s]?://(?:[A-Z]|[0-9]|[{}!$#-~_@.&+]|[!*\(\),] |(?:%[0-9A-F][0-9A-F]))+', txt, re.IGNORECASE)

        urls = [item.strip('.').strip() for item in urls]
        urls = list(set(urls))  # remove duplicates
        df_corpus.loc[i, 'URLS'] = ' | '.join(urls)  # save as single string
    except:
        pass

# save updated metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


################################################ SOURCE / COPYRIGHT INFO #####################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# new URLS column
df_corpus['SOURCES'] = ''

# loop through articles
for i, row in df_corpus.iterrows():
    if row['CORPUS'] == 'corpus_1':
        path_article = "D:/Data/corpus_1/unique/"
    elif row['CORPUS'] == 'corpus_2':
        path_article = "D:/Data/corpus_2/txt/"
    elif row['CORPUS'] == 'corpus_3':
        path_article = "D:/Data/corpus_3/unique_2/"

    print('Extracting sources from corpus/article:', row['CORPUS'], '/', row['POSTID'])

    try:
        with open(f"{path_article}{row['POSTID']}.txt", 'r', encoding='utf-8') as f:
            txt = f.read()
        sources = [item.split('.')[0].strip() for item in re.findall(r'(?<=©)(.*)(?=\n)', txt)]

        if len(sources) == 0:
            sources = [item.strip() for item in re.findall(r'(?<=copyright)(.*)(?=\n)', txt, re.IGNORECASE)]

        df_corpus.loc[i, 'SOURCES'] = ' | '.join(sources)

        # clean special characters
        sources = sources.replace('\xa0—\xa0', '-')
    except:
        pass

# save updated metadata file
df_corpus.to_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', index=None)


################################################## CHECK ACTIVE URLS #######################################################

# read metadata file (if previously saved)
df_corpus = pd.read_csv("D:/Data/corpus_common/corpus_tags.csv", sep=',', dtype=str, na_filter=False)

# web request
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.8,es;q=0.6', 'Connection': 'keep-alive'}
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# loop through articles
for i, row in df_corpus[:5].iterrows():
    if row['URLS'] != '':
        for url in row['URLS'].split('|'):
            status = 'Unknown'

            try:
                response = requests.get(url.strip(), headers=headers, timeout=5)

                if response.status_code == 404:
                    status = 'Not Found'
                elif response.status_code == 403:
                    status = 'Forbidden'
                elif response.status_code == 200:
                    if row['TITLE_CLEAN'].upper() in response.text.upper():
                        status = 'Confirmed'
            except:
                status = 'Invalid'

            print(row['POSTID'], status, url.strip())

    with open("D:/Data/corpus_common/corpus_tags_urls.tsv", 'a') as f:
        f.write(f"\n{row['POSTID']}\t{status}\t{url.strip()}")


################################################ DESCRIPTIVE STATISTICS ###################################################

# most common places
places = df_corpus[df_corpus['LOCATION'] != '']['LOCATION'].tolist()
list(map(lambda x: print(x), collections.Counter(places).most_common(50)))



x = {"a", "b", "c"}
y = {"f", "d", "a"}
z = {"c", "d", "e"}

x.union(y, z)
