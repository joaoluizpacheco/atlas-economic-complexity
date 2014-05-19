from observatory.models import Hs4_cpy, Sitc4_cpy, Country, Hs4, Sitc4

import re


# make sure app name is in the list of possible apps
def get_app_name(app_name):
    possible_apps = ["tree_map", "stacked", "product_space", "map"]

    # if the app_name requested is not in the list of possibilities
    if app_name not in possible_apps:
        app_name = None

    return app_name


# make sure this is accepted trade_flow
def get_trade_flow(trade_flow):
    possible_yoga_flows = ["export", "import", "net_export", "net_import"]

    if trade_flow not in possible_yoga_flows:
        trade_flow = None

    return trade_flow


def get_years(classification):
    # get distince years from db, different for diff product classifications

    if classification == "sitc4":
        years_available = list(
            Sitc4_cpy.objects.values_list(
                "year",
                flat=True).distinct())
    elif classification == "hs4":
        years_available = list(
            Hs4_cpy.objects.values_list(
                "year",
                flat=True).distinct())

    return years_available


# Returns app type in CCPY format
def get_app_type(country1, country2, product, year):

    # country / all / show / year
    if country2 == "all" and product == "show":
        return "casy"

    # country / show / all / year
    elif country2 == "show" and product == "all":
        return "csay"

    # show / all / product / year
    elif country1 == "show" and country2 == "all":
        return "sapy"

    # country / country / show / year
    elif product == "show":
        return "ccsy"

    #  country / show / product / year
    else:
        return "cspy"


# Returns the Country object or None
def get_country(country):
    # first try looking up based on 3 character code
    try:
        c = Country.objects.get(name_3char=country)
    except Country.DoesNotExist:
        # next try 2 character code
        try:
            c = Country.objects.get(name_2char=country)
        except Country.DoesNotExist:
            c = None
    return c


# Returns the Product object or None
def get_product(product, classification):
    # first try looking up based on 3 character code
    if classification == "hs4":
        try:
            p = Hs4.objects.get(code=product)
        except Hs4.DoesNotExist:
            # next try SITC4
            try:
                conv_code = Sitc4.objects.get(code=product).conversion_code
                p = Hs4.objects.get(code=conv_code)
            except Sitc4.DoesNotExist:
                p = None
    else:
        try:
            p = Sitc4.objects.get(code=product)
        except Sitc4.DoesNotExist:
            # next try SITC4
            try:
                conv_code = Hs4.objects.get(code=product).conversion_code
                p = Sitc4.objects.get(code=conv_code)
            except Hs4.DoesNotExist:
                p = None
    return p


def get_time_clause(years):
    """Generate a string like 'between 2005 and 2007' or 'in 2011' from a list
    of years. Beginning space is included to allow for empty time clause."""
    if years is None or len(years) == 0:
        return ""
    elif len(years) == 1:
        return " in %d" % years[0]
    else:
        return " between %d and %d" % (years[0], years[1])


def get_title(api_name, app_name, country_names=None, trade_flow=None,
              years=None, product_name=None):
    """Fetch the natural-languageized title of a page based on the data being
    displayed.

    :param api_name: One of: casy, cspy, csay, ccsy, sapy
    :param app_name: E.g. pie_scatter, stacked, product_space, rings ...
    :param list country_names: List of country name strings. If multiple, first
    is "from" country and second is the "to" country.
    :param str trade_flow: import, export, net_import, net_export
    :param list years: List of years. If multiple, first is the start year and
    second is the end year.
    :param str product_name: Localized name of product
    """

    # e.g. What did Burundi export in 2013? Which products are feasible for
    # Latvia?
    if api_name == "casy":
        if app_name == "pie_scatter":
            return "Which products are feasible for %s?" % country_names[0]
        else:
            return "What did %s %s%s?" % (country_names[0],
                                          trade_flow,
                                          get_time_clause(years))

    # e.g. Where did Albania export to in 2009?
    elif api_name == "csay":
        article = "to" if trade_flow == "export" else "from"
        return "Where did %s %s %s%s?" % (country_names[0],
                                          trade_flow,
                                          article,
                                          get_time_clause(years))

    # e.g. Who exported Petroleum in 1990?
    elif api_name == "sapy":
        return "Who %sed %s%s?" % (trade_flow, product_name,
                                   get_time_clause(years))

    # e.g. What did Germany import from Turkey in 2011?
    elif api_name == "ccsy":
        article = "to" if trade_flow == "export" else "from"
        return "What did %s %s %s %s%s?" % (country_names[0], trade_flow,
                                            article, country_names[1],
                                            get_time_clause(years))

    # e.g. Where did France export wine to in 2012?
    elif api_name == "cspy":
        article = "to" if trade_flow == "export" else "from"
        return "Where did %s %s %s %s%s?" % (country_names[0], trade_flow,
                                             product_name, article,
                                             get_time_clause(years))

    else:
        raise ValueError("Unknown API name when trying to generate title: %s" %
                         api_name)


def params_to_url(api_name=None, app_name=None, country_codes=None,
                  trade_flow=None, years=None, product_code=None):
    """Generate explore/ urls from specific parameters. Same parameter syntax
    as get_title, but product code instead of product name and 3 letter country
    codees instead of country names."""

    if app_name is None:
        # Treemap is a safe default that works with almost all of our data
        app_name = 'tree_map'

    if api_name == 'casy':
        # What did Germany import in 2012?
        # Which products are feasible for Latvia?
        # Looks like explore/tree_map/import/deu/all/show/2012/
        country_codes.append('all')
        product_code = "show"

    elif api_name == 'cspy':
        # Where did Germany import Swine from in 2012?
        # Looks like explore/tree_map/import/deu/show/0103/2012/
        country_codes.append('show')

    elif api_name == 'csay':
        # Where does germany import from?
        # Looks like explore/tree_map/import/deu/show/all/2012/
        country_codes.append('show')
        product_code = 'all'

    elif api_name == 'ccsy':
        # What did Germany import from Congo in 2012?
        # Looks like explore/tree_map/import/deu/cog/show/2012/
        product_code = 'show'

    elif api_name == 'sapy':
        # Who exports potatoes?
        # Looks like explore/tree_map/export/show/all/0101/2012/
        country_codes = ("show", "all")

    else:
        raise ValueError("Unknown API name : %s" % api_name)

    url = "explore/%s/%s/%s/%s/%s/" % (app_name, trade_flow, country_codes[0],
                                       country_codes[1], product_code)
    if years is not None:
        url += "%s/" % years

    return url

year_expressions = [
    re.compile(r'between (\d{4}) and (\d{4})', re.IGNORECASE),
    re.compile(r'from (\d{4}) to (\d{4})', re.IGNORECASE),
    re.compile(r'(\d{4}).*(\d{4})'),
    re.compile(r'(?:in|at|during) (\d{4})', re.IGNORECASE),
    re.compile(r'(\d{4})')
]


def extract_years(input_str):
    """Extract things that look like years out of a given plaintext."""
    results = (exp.search(input_str) for exp in year_expressions)
    results = [result for result in results if result is not None]

    if len(results) == 0:
        return None, None
    else:
        return results[0].span(), results[0].groups()
