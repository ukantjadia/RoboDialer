from backend.services.scrapers.bbb_scraper import scrape_bbb
from backend.services.scrapers.USA.superpages import scrape_superpages
from backend.services.scrapers.Canada.yellowpages_ca_scraper import scrape_yellowpages_ca
from backend.services.scrapers.google_maps_scraper import scrape_lead_by_industry
from backend.services.scrapers.USA.hotfrog_scraper import scrape_hotfrog
from backend.services.scrapers.USA.yellowpages_scraper import scrape_yellowpages
from backend.services.scrapers.Canada.hotfrog_ca_scraper import scrape_hotfrog_ca
from backend.services.scrapers.b2bstars_scraper import scrape_b2bstars

from backend.services.scrapers.UK.misterwhat_scraper import scrape_misterwhat_businesses
from backend.services.scrapers.UK.scoot_scraper import scrape_scoot_businesses
from backend.services.scrapers.UK.showmelocal_scraper import scrape_showmelocal_businesses
from backend.services.scrapers.UK.tradefinder_scraper import scrape_thetradefinder_businesses
from backend.services.scrapers.UK.uk_192_scraper import scrape_192_businesses
from backend.services.scrapers.UK.uk_directory_scraper import scrape_uksmallbusiness_directory
from backend.services.scrapers.UK.uk_locate_scraper import scrape_uk_locate_businesses
from backend.services.scrapers.UK.yell_scraper import new_scrape_yell_businesses
from backend.services.scrapers.UK.yelp_scraper import scrape_yelp_uk_businesses

from backend.services.scrapers.France.hotfrog_fr_scraper import scrape_hotfrog_fr
from backend.services.scrapers.France.bizin_scraper import scrape_bizin_businesses
from backend.services.scrapers.France.fr_11800_scraper import scrape_118000_businesses
from backend.services.scrapers.France.jaunes_scraper import scrape_pagesjaunes_businesses
from backend.services.scrapers.France.justacote_scraper import scrape_justacote_businesses
from backend.services.scrapers.France.tel_scraper import scrape_tel_businesses
from backend.services.scrapers.France.cylex_scraper import scrape_cylex_businesses


SCRAPERS = {
    "common": {
        "gmaps": scrape_lead_by_industry,
        "b2bstars": scrape_b2bstars
    },
    "USA": {
        "hotfrog_us": scrape_hotfrog,
        "superpages": scrape_superpages,
        "bbb": scrape_bbb,
        "yellowpages_us": scrape_yellowpages,
    },
    "CAN": {
        "yellowpages_ca": scrape_yellowpages_ca,
        "hotfrog_ca": scrape_hotfrog_ca,
        "bbb": scrape_bbb,
    },
    "UK": {
        "misterwhat_businesses": scrape_misterwhat_businesses,
        "scoot_businesses": scrape_scoot_businesses,
        "showmelocal_businesses": scrape_showmelocal_businesses,
        "thetradefinder_businesses": scrape_thetradefinder_businesses,
        # "192_businesses": scrape_192_businesses,
        "uksmallbusiness_directory": scrape_uksmallbusiness_directory,
        "uk_locate_businesses": scrape_uk_locate_businesses,
        "yell_businesses": new_scrape_yell_businesses,
        # "yelp_uk_businesses": scrape_yelp_uk_businesses,
    },
    "FRA": {
        "hotfrog_fr": scrape_hotfrog_fr,
        "bizin_fr": scrape_bizin_businesses,
        "fr_118000": scrape_118000_businesses,
        "pagesjaunes_fr": scrape_pagesjaunes_businesses,
        "justacote_fr": scrape_justacote_businesses,
        "tel_fr": scrape_tel_businesses,
        "cylex_fr": scrape_cylex_businesses,
    }
}
