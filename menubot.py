#!/usr/bin/env python
# encoding: utf-8
"""
Tweet a menu from NYPL's What's On The Menu
"""
from __future__ import print_function, unicode_literals
from whatsonthemenu import WhatsOnTheMenu  # pip install whatsonthemenu
# from pprint import pprint
import argparse
import random
import os
import tempfile
import sys
import twitter  # pip install twitter
import webbrowser
import yaml  # pip install pyaml

try:
    # Python 3
    from urllib.request import urlretrieve
except ImportError:
    # Python 2
    from urllib import urlretrieve


def timestamp():
    """ Print a timestamp and the filename with path """
    import datetime
    print(datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p") + " " +
          __file__)


def load_yaml(filename):
    """
    File should contain:
    consumer_key: TODO_ENTER_YOURS
    consumer_secret: TODO_ENTER_YOURS
    access_token: TODO_ENTER_YOURS
    access_token_secret: TODO_ENTER_YOURS
    nypl_menus_token: TODO_ENTER_YOURS
    """
    f = open(filename)
    data = yaml.safe_load(f)
    f.close()
    if not data.viewkeys() >= {
            'access_token', 'access_token_secret',
            'consumer_key', 'consumer_secret'}:
        sys.exit("Twitter credentials missing from YAML: " + filename)
    if not data.viewkeys() >= {
            'nypl_menus_token'}:
        sys.exit("NYPL Menus credentials missing from YAML: " + filename)
    return data


def tweet_it(string, credentials, image=None):
    """ Tweet string and image using credentials """
    if len(string) <= 0:
        return

    # Create and authorise an app with (read and) write access at:
    # https://dev.twitter.com/apps/new
    # Store credentials in YAML file
    auth = twitter.OAuth(
        credentials['access_token'],
        credentials['access_token_secret'],
        credentials['consumer_key'],
        credentials['consumer_secret'])
    t = twitter.Twitter(auth=auth)

    print("TWEETING THIS:\n", string)

    if args.test:
        print("(Test mode, not actually tweeting)")
    else:

        if image:
            print("Upload image")

            # Send images along with your tweets.
            # First just read images from the web or from files the regular way
            with open(image, "rb") as imagefile:
                imagedata = imagefile.read()
            t_up = twitter.Twitter(domain='upload.twitter.com', auth=auth)
            id_img = t_up.media.upload(media=imagedata)["media_id_string"]
        else:
            id_img = None  # Does t.statuses.update work with this?

        result = t.statuses.update(
            status=string, media_ids=id_img)

        url = "http://twitter.com/" + \
            result['user']['screen_name'] + "/status/" + result['id_str']
        print("Tweeted:\n" + url)
        if not args.no_web:
            webbrowser.open(url, new=2)  # 2 = open in a new tab, if possible


def getit(dictionary, key):
    """Wrapper for getting values from a dict"""
    value = dictionary[key]
    try:
        value = value.strip()
    except AttributeError:
        pass
    print(key, value)
    return value


def make_tweet(tweet, link):
    """ Remove extra space, append link """
    tweet = strip_duplicate_whitespace(tweet)
    tweet += " " + link
    print(len(tweet), tweet)
    return tweet


def strip_duplicate_whitespace(text):
    """ Remove duplicate whitespace """
    #  Side effect: other whitespace turned into space
    return " ".join(text.split())


def outfilename(menu_id, page_no, ext="jp2"):
    """ Make a filename for the image from menu ID and page number """
    outfile = str(menu_id) + "-" + str(page_no) + "." + ext
    return outfile


def create_dir(dir):
    if not os.path.isdir(dir):
        os.mkdir(dir)


def download_file_to_tmp(url, menu_id, page_no):
    outdir = os.path.join(tempfile.gettempdir(), "menubot")
    create_dir(outdir)
    outfile = os.path.join(outdir, outfilename(menu_id, page_no))
    print("Saving\n", url, "\nto\n", outfile)
    download_file(url, outfile)
    return outfile


def download_file(url, outfile):
    """Download file at url to outfile"""
    if not args.test:
        urlretrieve(url, outfile)


def get_a_random_menu(api):
    # Pick random dates and sort
    min_year = random.randint(1851, 2007)
    max_year = random.randint(min_year + 1, min_year + 11)
    sort_by = random.choice(["date", "name", "dish_count"])
#     status: "?status=under_review" || "?status=complete" ||
#             "?status=to_transcribe"
    print(min_year, max_year, sort_by)

    menus = api.get_menus(min_year=min_year, max_year=max_year,
                          sort_by=sort_by)
    # Pick the first menu
    menu = menus['menus'][0]
    # pprint(menu)
    return menu


def menu_tweet(menu):
    """Main thing to make a tweet from this menu"""
    menu_id = menu['id']
    print(menu_id)

    # TESTING
#     menu_id = 29388
#     menu = api.get_menus_id(menu_id)
    # TESTING

    # Get pages from a certain menu
    pages = api.get_menus_id_pages(menu_id)
    # pprint(pages)

    homepage = "http://menus.nypl.org/menus/" + str(menu_id)
    print(homepage)

    location = getit(menu, 'location')
    # place = getit(menu, 'place')
    year = getit(menu, 'year')

    # For now, just get a random page
    # TODO if <= 4 pages, get all
    # TODO if > 4 pages, get 4 random ones
    number_of_pages = len(pages['pages'])
    print("number_of_pages", number_of_pages)

    random_page_index = random.randrange(0, number_of_pages)
    print("random_page_index", random_page_index)

    random_page = pages['pages'][random_page_index]

    img_url = random_page['large_src_jp2']
    print("img_url", img_url)

    # Download it to temp
    outfile = download_file_to_tmp(img_url, menu_id, random_page_index)

    # Find a dish from this page
    dishes = random_page['dishes']
    random.shuffle(dishes)
    dish = None
    price = None
    print("Dishes found", len(dishes))
    while dishes:
        random_dish = dishes.pop()
        print(random_dish)
        dish = getit(random_dish, 'name')
        # Can quickly reject some
        if len(dish) > 140:
            continue
        price = getit(random_dish, 'price')
        break

    currency_symbol = menu['currency_symbol']
    currency = menu['currency']
    print("currency", currency_symbol, currency)

    # Make a tweet

    chance = random.randint(0, 99)
    while chance < 100:
        tweet = None
        print("chance", chance)

        if chance < 60:

            if currency_symbol and price:

                second_roll = random.randint(0, 99)
                print("second_roll", second_roll)

                if second_roll < 33:
                    tweet = "Only {0}{1} for {2} at {3}? Bargain!".format(
                        currency_symbol, price, dish, location)

                elif second_roll < 67:
                    tweet = "In {0}, {1} for only {2}{3} at {4}".format(
                        year, dish, currency_symbol, price, location)

                else:
                    tweet = "{1}, {2}{3}, {4} ({0})".format(
                        year, dish, currency_symbol, price, location)

        if not tweet and chance < 80:

            if dish:

                second_roll = random.randint(0, 99)
                print("second_roll", second_roll)

                if second_roll < 30:
                    tweet = ("Welcome to {0}! Why not enjoy some {1} "
                             "at {2}?"). format(year, dish, location)

                elif second_roll < 60:
                    tweet = "Why not enjoy some {0} at {1}?".format(
                        dish, location)

                elif second_roll < 90:
                    tweet = "Welcome to {0}, may I recommend the {1}?".format(
                        location, dish)

                elif second_roll < 95:
                    tweet = "{0}, {1} ({2})".format(dish, location, year)

                else:
                    tweet = "{0}, {1}".format(dish, location)

        if not tweet:
            second_roll = random.randint(0, 99)
            print("second_roll", second_roll)

            if second_roll < 60:
                tweet = "Welcome to {0}, would you care for the menu?".format(
                    location)

            elif second_roll < 85:
                tweet = "{0} menu for {1}".format(year, location)

            else:
                tweet = "{1} ({0})".format(year, location)

        print(tweet)
        tweet = make_tweet(tweet, homepage)
        # 24 characters for photo attachments leaves 116 characters
        if len(tweet) <= 116:
            # Bingo!
            break
        else:
            print("too long")

        # Tweet too long? Keep trying
        chance += 1

    if not tweet:
        print("failsafe")
        tweet = location
        tweet = make_tweet(tweet, homepage)

    if len(tweet) > 116:
        print("failsafe 2")
        tweet = homepage

    print(tweet)
    return tweet, outfile


if __name__ == "__main__":
    timestamp()

    parser = argparse.ArgumentParser(
        description="Tweet a menu from NYPL's What's On The Menu",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-y', '--yaml',
        default='/Users/hugo/Dropbox/bin/data/menubot.yaml',
        help="YAML file location containing Twitter keys and secrets")
    parser.add_argument(
        '-c', '--chance',
        type=int, default=4,
        help="Denominator for the chance of tweeting this time")
    parser.add_argument(
        '-nw', '--no-web', action='store_true',
        help="Don't open a web browser to show the tweeted tweet")
    parser.add_argument(
        '-x', '--test', action='store_true',
        help="Test mode: go through the motions but don't tweet anything"
              "or download any images")
    args = parser.parse_args()

    # Do we have a chance of tweeting this time?
    if random.randrange(args.chance) > 0:
        sys.exit("No tweet this time")

    credentials = load_yaml(args.yaml)

    # Ask NYPL for a token: https://github.com/NYPL/menus-api#tokens
    api = WhatsOnTheMenu(credentials['nypl_menus_token'])

    # Need a random menu
    menu = get_a_random_menu(api)

    tweet, outfile = menu_tweet(menu)

    tweet_it(tweet, credentials, outfile)

    # Show rate limit
    # print("Rate limit remaining: ", api.rate_limit_remaining())


# End of file
