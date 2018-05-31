#!/usr/bin/env python3

import re
import requests


def mysql_quote(x):
    """Quote the string x using MySQL quoting rules. If x is the empty string,
    return "NULL". Probably not safe against maliciously formed strings, but
    our input is fixed and from a basically trustable source."""
    if not x:
        return "NULL"
    x = x.replace("\\", "\\\\")
    x = x.replace("'", "''")
    x = x.replace("\n", "\\n")
    return "'{}'".format(x)


def main():
    print("""insert into donations (donor, donee, amount, donation_date,
    donation_date_precision, donation_date_basis, cause_area, url,
    donor_cause_area_url, notes, affected_countries, affected_states,
    affected_cities, affected_regions, amount_original_currency, original_currency, currency_conversion_date, currency_conversion_basis) values""")

    first = True

    with open("data.txt", "r") as f:
        next(f)  # skip header row
        for line in f:
            url, grantee, amount, funding_type, term, notes = line[:-1].split("\t")

            if url.startswith("http://www.thesff.com/water-and-sanitation/"):
                focus_area = "Water and sanitation"
                focus_area_url = "http://www.thesff.com/water-and-sanitation/"
            elif url == "http://www.thesff.com/jibu/":
                # Jibu is the only URL that has its own root-level page, but it
                # is listed along with the other water and sanitation
                # charities.
                focus_area = "Water and sanitation"
                focus_area_url = "http://www.thesff.com/water-and-sanitation/"
            elif url.startswith("http://www.thesff.com/mental-health/"):
                focus_area = "Mental health"
                focus_area_url = "http://www.thesff.com/mental-health/"
            elif url.startswith("http://www.thesff.com/disadvantaged-youth/"):
                focus_area = "Disadvantaged youth"
                focus_area_url = "http://www.thesff.com/disadvantaged-youth/"

            donation_date = ""
            donation_date_precision = ""
            m = re.match(r"(\d\d\d\d) to \d\d\d\d", term)
            if m:
                donation_date = m.group(1) + "-01-01"
                donation_date_precision = "year"

            amount_original_currency = "NULL"
            original_currency = ""
            currency_conversion_date = ""
            currency_conversion_basis = ""
            if amount.startswith("$"):
                # USD
                amount = amount.replace("$", "").replace(",", "")
            else:
                if amount.startswith("£"):
                    original_currency = "GBP"
                    currency_symbol = "£"
                else:
                    assert amount.startswith("€")
                    original_currency = "EUR"
                    currency_symbol = "€"

                currency_conversion_date = donation_date
                # Safi Sana requires a currency conversion but doesn't have a
                # start date for its term. I'm taking November 2016 from the
                # URL of
                # http://thesff.com/system/wp-content/uploads/2016/11/Safi-Sana-Brochure-2pager.pdf
                # which I found on the Safi Sana page
                # (http://www.thesff.com/water-and-sanitation/waste-to-resource/safi-sana/).
                if grantee == "Safi Sana":
                    currency_conversion_date = "2016-11-15"
                if not currency_conversion_date:
                    raise ValueError(("conversion date is not set", grantee))
                r = requests.get("https://api.fixer.io/{}?base={}"
                                 .format(currency_conversion_date,
                                         original_currency))
                j = r.json()
                amount_original_currency = float(amount.replace(currency_symbol, "").replace(",", ""))
                amount = j["rates"]["USD"] * amount_original_currency
                currency_conversion_basis = "Fixer.io"

            print(("    " if first else "    ,") + "(" + ",".join([
                mysql_quote("Stone Family Foundation"),  # donor
                mysql_quote(grantee),  # donee
                str(amount),  # amount
                mysql_quote(donation_date),  # donation_date
                mysql_quote(donation_date_precision),  # donation_date_precision
                mysql_quote("donation log"),  # donation_date_basis
                mysql_quote(focus_area),  # cause_area
                mysql_quote(url),  # url
                mysql_quote(focus_area_url),  # donor_cause_area_url
                mysql_quote(notes),  # notes
                mysql_quote(""),  # affected_countries
                mysql_quote(""),  # affected_states
                mysql_quote(""),  # affected_cities
                mysql_quote(""),  # affected_regions
                str(amount_original_currency),  # amount_original_currency
                mysql_quote(original_currency),  # original_currency
                mysql_quote(currency_conversion_date),  # currency_conversion_date
                mysql_quote(currency_conversion_basis),  # currency_conversion_basis
            ]) + ")")
            first = False
        print(";")


if __name__ == "__main__":
    main()
