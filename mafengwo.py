from common import element_xpaths
import mtranslate
import urllib3
from bs4 import BeautifulSoup
import pandas as pd
from textblob import TextBlob
from pathlib import Path
import os
import shutil


def save_to_excel(df, path_to_save):
    # noinspection PyTypeChecker
    writer = pd.ExcelWriter(path_to_save, engine='xlsxwriter', options={'strings_to_urls': False})
    df.to_excel(writer)
    writer.close()
    print(f'Saved data to excel successfully in {path_to_save}')


def save_to_file(review, path_to_file):
    with open(path_to_file, 'w') as f:
        f.write(review)
    print(f'Saved data to file successfully in {path_to_file}')


def positivity(txt):
    tb = TextBlob(txt)
    pos = tb.sentiment.polarity
    print('pos ', pos)
    return pos


def get_web_page(url):
    req = urllib3.PoolManager()
    res = req.request('GET', url)
    page = BeautifulSoup(res.data, 'html.parser')
    return page


def make_500_chunks(reviews):
    chunks = []
    united_reviews = ''
    for review in reviews:
        if len(united_reviews) > 300:
            chunks.append(united_reviews)
            united_reviews = ''

        united_reviews += review
    return chunks


def get_review_text(page):
    try:
        reviews = page.find(attrs={'class': element_xpaths.review_whole_class}).stripped_strings
    except AttributeError:
        print('Going alternative')
        reviews = page.find(attrs={'class': element_xpaths.review_whole_alternate_class})
        reviews.find(attrs={'class': element_xpaths.review_summary_class}).decompose()
        reviews = reviews.stripped_strings

    reviews = list(reviews)
    print(reviews)
    original = ' '.join(reviews)

    chunks = make_500_chunks(reviews)
    translated = []

    iteration = 0
    for chunk in chunks:
        iteration += 1
        print('translation iter ', iteration)
        trans_chunk = mtranslate.translate(to_translate=chunk, to_language='en', from_language='zh-CN')
        translated.append(trans_chunk)

    translated = ' '.join(translated)
    return original, translated


def get_dates_published_links(page, base_url):
    reviews = page.find_all(name='li', attrs={'class': element_xpaths.reviews_list_class})
    links = []
    dates_published = []
    for review in reviews:
        date = review.find(name='span', attrs={'class': element_xpaths.review_date_class}).text
        dates_published.append(date)

        link_containter = review.find(name='a', attrs={'class': element_xpaths.review_titles_class})
        link = base_url + link_containter.get('href')
        links.append(link)

    return dates_published, links


def is_next_available(page):
    try:
        next_link = page.find(name='a', attrs={'class': element_xpaths.next_page_reference_class}).text
        print('available: ', next_link)
        return True
    except Exception:
        print('nope, not available')
        return False


def open_next_page(curr_page, base_url):
    next_page_link_container = curr_page.find(name='a', attrs={'class': element_xpaths.next_page_reference_class})
    next_url = base_url + next_page_link_container.get('href')
    print('next link ', next_url)
    return get_web_page(next_url)


def clean_data_directory(directory_path):
    try:
        shutil.rmtree(directory_path)
    except Exception as e:
        print('Exception while removing directory ', str(e))
    os.mkdir(directory_path)


def get_inputs(platform):
    key_word_used = input(f'Input the keyword used please: ')
    try:
        num_of_reviews_to_get = input(f'Input the number of reviews to process please: ')
        num_of_reviews_to_get = int(num_of_reviews_to_get)
        if num_of_reviews_to_get < 1:
            raise Exception
    except Exception:
        print(f'Invalid number of reviews passed - expecting a positive integer.')
        return

    try:
        reviews_first_page_url = input(f'Input the url of reviews page from {platform} please: ')
        all_reviews_page = get_web_page(reviews_first_page_url)
    except Exception:
        print('An error occurred while opening the url. Perhaps an invalid url or no internet connection?')
        return
    print('opened page')

    return key_word_used, all_reviews_page, num_of_reviews_to_get


def init_variables():
    columns = 'Key Word Used', 'Platform', 'Review URL', 'Date', 'Review (Chinese)', \
              'Translation (English)', 'Positive or Negative'
    # reviews_first_page_url = 'http://www.mafengwo.cn/yj/52088/'
    # reviews_first_page_url = 'http://www.mafengwo.cn/yj/10189/'
    # reviews_first_page_url = 'http://www.mafengwo.cn/travel-scenic-spot/mafengwo/10684.html'
    platform = 'mafengwo'
    base_url = 'http://www.mafengwo.cn'
    key_word_used, all_reviews_page, num_of_reviews_to_get = get_inputs(platform)
    print('cleaned directory')
    # start_number = len(os.listdir(Path(platform)))
    start_number = 0
    curr_review_number = 0
    print(f'start number {start_number}')

    path_to_excel = Path(f'data/{platform}.xlsx')
    return all_reviews_page, base_url, columns, curr_review_number, \
           key_word_used, num_of_reviews_to_get, platform, start_number, path_to_excel


def main():
    all_reviews_page, base_url, columns, curr_review_number, key_word_used, \
    num_of_reviews_to_get, platform, start_number, path_to_excel = init_variables()

    clean_data_directory(directory_path=Path('data/reviews'))

    data = []
    review_num_reached = False
    while is_next_available(all_reviews_page) and not review_num_reached:
        dates_published, links = get_dates_published_links(all_reviews_page, base_url)
        print('got links')
        print(f'going for review number {curr_review_number}')

        for date_published, url in zip(dates_published, links):
            # noinspection PyBroadException
            try:
                print('================================================')
                print('curr url ', url)
                review_page = get_web_page(url)

                print('translating')
                chinese_review, translated_review = get_review_text(review_page)

                print('getting pos')
                pos = positivity(translated_review)

                path_to_chinese_review = Path(f'data/reviews/review_original_{start_number}.txt')
                path_to_translated_review = Path(f'data/reviews/review_translated_{start_number}.txt')

                save_to_file(review=chinese_review, path_to_file=path_to_chinese_review)
                save_to_file(review=translated_review, path_to_file=path_to_translated_review)

                data.append((key_word_used, base_url, url, date_published,
                             path_to_chinese_review, path_to_translated_review, pos))
                start_number += 1
                curr_review_number += 1

                if curr_review_number >= num_of_reviews_to_get:
                    review_num_reached = True
                    print(f'Review num reached - {curr_review_number}')
                    break

                if curr_review_number % 5 == 0:
                    df = pd.DataFrame(columns=columns, data=data)
                    save_to_excel(df, path_to_save=path_to_excel)

            except Exception as e:
                print(f'Exc {e}')

        all_reviews_page = open_next_page(curr_page=all_reviews_page, base_url=base_url)

    if not review_num_reached:
        print(f'Reached the end of reviews while trying to get {num_of_reviews_to_get} reviews.'
              f' The actual number of reviews is {curr_review_number}')

    if curr_review_number == 0:
        print(f'Could not find any reviews in the given url.')
        return

    # TODO append to excel file not overwrite completely
    df = pd.DataFrame(columns=columns, data=data)
    save_to_excel(df, path_to_save=path_to_excel)
    print('Success !')
    pass


if __name__ == '__main__':
    main()
    pass
