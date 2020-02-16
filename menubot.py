#!/usr/bin/env python
# encoding: utf-8
"""
Tweet a menu from NYPL's What's On The Menu
"""
# from pprint import pprint
import argparse
import os
import random
import sys
import tempfile
import webbrowser
from urllib.request import urlretrieve

import pytumblr  # pip install pytumblr
import twitter  # pip install twitter
import yaml  # pip install pyyaml
from whatsonthemenu import WhatsOnTheMenu  # pip install whatsonthemenu


MAX_TWEET = 280


def timestamp():
    """ Print a timestamp and the filename with path """
    import datetime

    print(datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p") + " " + __file__)


def load_yaml(filename):
    """
    File should contain:
    consumer_key: TODO_ENTER_YOURS
    consumer_secret: TODO_ENTER_YOURS
    access_token: TODO_ENTER_YOURS
    access_token_secret: TODO_ENTER_YOURS
    nypl_menus_token: TODO_ENTER_YOURS
    """
    with open(filename) as f:
        data = yaml.safe_load(f)

    keys = data.viewkeys() if sys.version_info.major == 2 else data.keys()
    if not keys >= {
        "access_token",
        "access_token_secret",
        "consumer_key",
        "consumer_secret",
    }:
        sys.exit("Twitter credentials missing from YAML: " + filename)
    if not keys >= {
        "tumblr_consumer_key",
        "tumblr_consumer_secret",
        "tumblr_oauth_token",
        "tumblr_oauth_secret",
    }:
        sys.exit("Tumblr credentials missing from YAML: " + filename)
    if not keys >= {"nypl_menus_token"}:
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
        credentials["access_token"],
        credentials["access_token_secret"],
        credentials["consumer_key"],
        credentials["consumer_secret"],
    )
    t = twitter.Twitter(auth=auth)

    print("TWEETING THIS:\n" + string)

    if args.test:
        print("(Test mode, not actually tweeting)")
    else:

        if image:
            print("Upload image")

            # Send images along with your tweets.
            # First just read images from the web or from files the regular way
            with open(image, "rb") as imagefile:
                imagedata = imagefile.read()
            t_up = twitter.Twitter(domain="upload.twitter.com", auth=auth)
            id_img = t_up.media.upload(media=imagedata)["media_id_string"]
        else:
            id_img = None  # Does t.statuses.update work with this?

        result = t.statuses.update(status=string, media_ids=id_img)

        url = (
            "http://twitter.com/"
            + result["user"]["screen_name"]
            + "/status/"
            + result["id_str"]
        )
        print("Tweeted:\n" + url)
        if not args.no_web:
            webbrowser.open(url, new=2)  # 2 = open in a new tab, if possible


def tumblr_it(string, credentials, image, tags, homepage):
    """ Post to Tumblr """
    client = pytumblr.TumblrRestClient(
        credentials["tumblr_consumer_key"],
        credentials["tumblr_consumer_secret"],
        credentials["tumblr_oauth_token"],
        credentials["tumblr_oauth_secret"],
    )

    # Remove None tags
    tags = [tag for tag in tags if tag is not None]

    if args.test:
        print("(Test mode, not actually tumblring)")
    else:
        result = client.create_photo(
            "menubot",
            state="published",
            tags=tags,
            data=str(image),
            caption=str(string),
            link=homepage,
        )
        print(result)

        url = "http://menubot.tumblr.com/post/" + str(result["id"])
        print("Tumblred:\n" + url)
        if not args.no_web:
            webbrowser.open(url, new=2)  # 2 = open in a new tab, if possible


def getit(dictionary, key):
    """Wrapper for getting values from a dict"""
    value = dictionary[key]
    try:
        value = value.strip()
    except AttributeError:
        pass
    return value


def make_tweet(tweet, link):
    """ Remove extra space, append link """
    tweet = strip_duplicate_whitespace(tweet)
    tweet += " " + link
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

    menus = api.get_menus(min_year=min_year, max_year=max_year, sort_by=sort_by)
    # Pick the first menu
    menu = menus["menus"][0]
    # pprint(menu)
    return menu


def menu_tweet(menu):
    """Main thing to make a tweet from this menu"""
    menu_id = menu["id"]
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

    location = getit(menu, "location")
    # place = getit(menu, 'place')
    year = getit(menu, "year")

    # For now, just get a random page
    # TODO if <= 4 pages, get all
    # TODO if > 4 pages, get 4 random ones
    number_of_pages = len(pages["pages"])
    print("number_of_pages", number_of_pages)

    random_page_index = random.randrange(0, number_of_pages)
    print("random_page_index", random_page_index)

    random_page = pages["pages"][random_page_index]

    img_url = random_page["large_src_jp2"]
    print("img_url", img_url)

    # Download it to temp
    outfile = download_file_to_tmp(img_url, menu_id, random_page_index)

    # Find a dish from this page
    dishes = random_page["dishes"]
    random.shuffle(dishes)
    dish = None
    price = None
    print("Dishes found", len(dishes))
    while dishes:
        random_dish = dishes.pop()
        print(random_dish)
        dish = getit(random_dish, "name")
        # Can quickly reject some
        if len(dish) > MAX_TWEET:
            continue
        price = getit(random_dish, "price")
        break

    currency_symbol = menu["currency_symbol"]
    currency = menu["currency"]
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
                    tweet = (
                        f"Only {currency_symbol}{price} for {dish} at {location}?"
                        f" Bargain!"
                    )

                elif second_roll < 67:
                    tweet = (
                        f"In {year}, {dish} for only {currency_symbol}{price} at "
                        f"{location}"
                    )

                else:
                    tweet = f"{dish}, {currency_symbol}{price}, {location} ({year})"

        if not tweet and chance < 80:

            if dish:

                second_roll = random.randint(0, 99)
                print("second_roll", second_roll)

                if second_roll < 30:
                    tweet = (
                        f"Welcome to {year}! Why not enjoy some {dish} at {location}?"
                    )

                elif second_roll < 60:
                    tweet = f"Why not enjoy some {dish} at {location}?"

                elif second_roll < 90:
                    tweet = f"Welcome to {location}, may I recommend the {dish}?"

                elif second_roll < 95:
                    tweet = f"{dish}, {location} ({year})"

                else:
                    tweet = f"{dish}, {location}"

        if not tweet:
            second_roll = random.randint(0, 99)
            print("second_roll", second_roll)

            if second_roll < 60:
                tweet = f"Welcome to {location}, would you care for the menu?"

            elif second_roll < 85:
                tweet = f"{year} menu for {location}"

            else:
                tweet = f"{location} ({year})"

        print(tweet)
        tweet = make_tweet(tweet, homepage)
        # 24 characters for photo attachments
        if len(tweet) <= MAX_TWEET - 24:
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

    if len(tweet) > MAX_TWEET - 24:
        print("failsafe 2")
        tweet = homepage

    tags = ["menubot", "What's On The Menu?", "NYPL", str(year), location, dish]
    print(tags)

    print(tweet)
    return tweet, outfile, tags, homepage


def percent_chance(percent):
    return random.random() < percent / 100.0


if __name__ == "__main__":
    timestamp()

    parser = argparse.ArgumentParser(
        description="Tweet a menu from NYPL's What's On The Menu",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-y",
        "--yaml",
        default="/Users/hugo/Dropbox/bin/data/menubot.yaml",
        help="YAML file location containing Twitter keys and secrets",
    )
    parser.add_argument(
        "-c",
        "--chance",
        type=float,
        default=12.5,
        help="Percent chance of tweeting this time",
    )
    parser.add_argument(
        "-nw",
        "--no-web",
        action="store_true",
        help="Don't open a web browser to show the tweeted tweet",
    )
    parser.add_argument(
        "-x",
        "--test",
        action="store_true",
        help="Test mode: go through the motions but don't tweet anything "
        "or download any images",
    )
    args = parser.parse_args()

    # Do we have a chance of tweeting this time?
    if not percent_chance(args.chance):
        sys.exit("No tweet this time")

    credentials = load_yaml(args.yaml)

    # Ask NYPL for a token: https://github.com/NYPL/menus-api#tokens
    api = WhatsOnTheMenu(credentials["nypl_menus_token"])

    # Need a random menu
    menu = get_a_random_menu(api)

    tweet, outfile, tags, homepage = menu_tweet(menu)

    tumblr_it(tweet, credentials, outfile, tags, homepage)
    try:
        tweet_it(tweet, credentials, outfile)
    except twitter.api.TwitterHTTPError as e:
        # twitter.api.TwitterHTTPError: Twitter sent status 403 for URL:
        # 1.1/media/upload.json using parameters: (oauth_consumer_key=...&oauth_nonce=..
        # .&oauth_signature_method=HMAC-SHA1&oauth_timestamp=...&oauth_token=...&oauth_v
        # ersion=1.0&oauth_signature=...)
        # details: {'errors': [{'code': 326, 'message': 'To protect our users from spam
        # and other malicious activity, this account is temporarily locked. Please log
        # in to https://twitter.com to unlock your account.'}]}
        print(e)

    # Show rate limit
    # print("Rate limit remaining: ", api.rate_limit_remaining())

    # Delete the image file
    if not args.test:
        os.remove(outfile)


# End of file
