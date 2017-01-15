from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import logging
from read_cfg import read_cfg
import os
import time
import getopt
import sys
import csv
import smtplib

logger = logging.getLogger('alert')
cfg = read_cfg()
driver = webdriver.Chrome()
whl = "#busyindicator svg"


def alert():

    # for testing and setting up csv file
    # _write_row_csv(['Name', 'Status', 'Phone', 'Failure', 'Amount', 'Date'])

    driver.get(cfg['site_url'])

    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'BusinessCode'))).send_keys(cfg['code'])
    driver.find_element_by_css_selector('#UserName').send_keys(cfg['username'])
    driver.find_element_by_css_selector('#Password').send_keys(cfg['pass'])
    driver.find_element_by_css_selector('.button-area button').click()

    _wait_for_spinning_wheel_loaded()

    time.sleep(2)

    _navigate_to_customer_page()

    tbl_tr = ".clickable-table tr.trk_customer_record"
    els = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, tbl_tr)))
    for r_, el in enumerate(els, 1):
        logger.debug('Row ({}): {}'.format(r_, el.text))
    logger.info('Total rows (users) found: {}'.format(len(els)))

    ppl_to_alert = []
    for i in range(1, len(els) + 1):
        person_to_alert = []
        for y in range(1, 8):
            item = "tr.trk_customer_record:nth-of-type({})>td:nth-of-type({})".format(i, y)
            el = driver.find_element_by_css_selector(item)
            row_data = el.text.strip()
            # logger.debug(row_data)
            if y in [1, 2, 5]:
                person_to_alert.append(row_data)

        # only Active people
        # Ended people are omitted
        logger.info('User: {}, state: {}'.format(person_to_alert[0], person_to_alert[1]))
        if person_to_alert[1] == "Active":
            item = "tr.trk_customer_record:nth-of-type({})>td:nth-of-type(1)".format(i)
            driver.find_element_by_css_selector(item).click()

            # spinning wheel appears twice
            for _ in range(2):
                _wait_for_spinning_wheel_loaded()
            time.sleep(2)
            _document_ready()

            logger.info("Fetching users direct debits: {}".format(person_to_alert[0]))

            tbl_tr_ = '.clickable-table .debit-details'
            els_ = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, tbl_tr_)))

            # scan the table for Failed
            # break if Success or Written off appears first
            for row_ in range(1, len(els_) + 1):
                item = ".debit-details:nth-of-type({})".format(row_)
                el = driver.find_element_by_css_selector(item)
                line_= el.text.strip()
                logger.info(line_)
                if line_.count('Success') or line_.count('Written-Off'):
                    # break  UNCOMMENT !!!
                    pass
                elif line_.count('Failed'):
                    for td_ in range(2, 5):
                        it_ = ".debit-details:nth-of-type({})>td:nth-of-type({})".format(row_, td_)
                        td_text_ = driver.find_element_by_css_selector(it_).text
                        td_text_ = td_text_.replace('\n',' ')
                        person_to_alert.append(td_text_)
                    email_ = _get_email(person_to_alert[0])
                    person_to_alert.append(email_)
                    # all data retrieved
                    # add to people to alert
                    ppl_to_alert.append(person_to_alert)
                    break

            _navigate_to_customer_page()

    csv_ = _read_alerts()
    for prs_ in ppl_to_alert:
        for csv_alert in csv_:
            # user name and date
            # if match we dont send out
            if prs_[0] == csv_alert[0] and prs_[5] == csv_alert[5]:
                logger.info('Alert already sent: {}'.format(prs_))
                break
        else:
            _text_message(prs_)
            _send_email(prs_)
            _write_alert(prs_)

    time.sleep(1)


def _document_ready():
    try:
        WebDriverWait(driver, 20).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        logger.debug('Document ready')
    except TimeoutException:
        logger.warning('Document not ready!')


def _wait_for_spinning_wheel():
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, whl)))
    except TimeoutException:
        logger.debug('Spinning wheel has not appeared')


def _wait_for_spinning_wheel_loaded():

    _wait_for_spinning_wheel()
    for _ in range(60):
        try:
            WebDriverWait(driver, 0.5).until_not(EC.presence_of_element_located((
                By.CSS_SELECTOR, whl)))
            return True
        except TimeoutException:
            logger.debug('Spinning the page. Updating')


def _write_alert(row):
    with open('alerts.csv', 'ab') as hlr:
        wrt = csv.writer(hlr, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        wrt.writerow(row)
        logger.info('Alert added to .csv file: {}'.format(row))


def _read_alerts():
    with open('alerts.csv', 'rb') as hlr:
        rd = csv.reader(hlr, delimiter=',', quotechar='"')
        return [row for row in rd if row[1] != "Status"]


def _navigate_to_customer_page():

    try:
        driver.get(cfg['customers_url'])
        time.sleep(2)
        _wait_for_spinning_wheel_loaded()
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.showMore-button'))).click()
        logger.debug('Show more clicked')
        _wait_for_spinning_wheel()
        _wait_for_spinning_wheel_loaded()
    except:
        logger.error('_navigate_to_customer_page failed: ', exc_info=True)


def _get_email(name_):
    try:
        with open('users.csv', 'rb') as hlr:
            rd = csv.reader(hlr, delimiter=',', quotechar='"')
            users_ = [row for row in rd if row[1] != "Name"]
        for user_ in users_:
            if user_[0] == name_ and user_[1] != '':
                logger.debug('Email found: {}  for user: {}'.format(user_[1], user_[0]))
                return user_[1]
        else:
            logger.debug('Email not found for: {}'.format(user_[0]))
    except:
        logger.error('_get_email failed: ', exc_info=True)


def _text_message(text_recipient):
    logger.debug('Texting: {}'.format(text_recipient))

    # recipient
    if cfg['test'].lower() == 'true':
        msg_recipient = cfg['twilio_to_test']
        logger.debug('Test mode text recipient: {}'.format(msg_recipient))
    else:
        msg_recipient = text_recipient[2][1:]


def _send_email(user__):
    logger.debug('Emailing: {}'.format(user__))

    # recipient
    if cfg['test'].lower() == 'true':
        recipient = cfg['gmail_user']
        logger.debug('Test mode email recipient: {}'.format(recipient))
    else:
        recipient = user__[6]

    if not recipient:
        logger.info('Email not provided, hence not sent out: {}'.format(user__[0]))
        return
    elif cfg['gmail_method'] == 'less-secure':

        gmail_user = cfg['gmail_user']
        gmail_pwd = cfg['gmail_pwd']
        email_sender = cfg['gmail_user']
        email_subject = 'Payment failed'
        email_text = 'Dear Sirs.... Test'

        # Prepare actual message
        message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (email_sender, ", ".join(recipient), email_subject, email_text)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pwd)
            server.sendmail(email_sender, recipient, message)
            server.close()
            logger.info('Email sent to: {}'.format(recipient))
        except:
            logger.error('Email failed to send to: {}'.format(recipient), exc_info=True)


if __name__ == '__main__':
    verbose = None

    timestamp = time.strftime('%d%m%y', time.localtime())
    log_file = os.path.join(os.path.dirname(__file__), 'logs',
                            timestamp + ".log")
    file_hndlr = logging.FileHandler(log_file)
    logger.addHandler(file_hndlr)
    console = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(console)
    ch = logging.Formatter('[%(levelname)s] %(message)s')
    console.setFormatter(ch)
    file_hndlr.setFormatter(ch)

    argv = sys.argv[1:]
    opts, args = getopt.getopt(argv, "c:v", ["csv=", "verbose"])
    for opt, arg in opts:
        if opt in ("-c", "--csv"):
            csv_file = arg
        elif opt in ("-v", "--verbose"):
            verbose = True

    if verbose:
        logger.setLevel(logging.getLevelName('DEBUG'))
    else:
        logger.setLevel(logging.getLevelName('INFO'))
    logger.debug('CLI args: {}'.format(opts))
    alert()
    driver.quit()