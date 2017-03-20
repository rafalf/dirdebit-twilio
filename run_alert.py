from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from twilio.rest import TwilioRestClient
import logging
import os
import time
import getopt
import sys
import csv
import smtplib

logger = logging.getLogger('alert')

# config file
cfg = {}
with open('alerts.conf') as hlr:
    for line in hlr:
        split_line = line.split('::')
        cfg[split_line[0].strip()] = split_line[1].strip()

# driver
if cfg['browser'] == 'Chrome-OSX':
    driver = webdriver.Chrome()
elif cfg['browser'] == 'Chrome':
    driver_path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe')
    driver = webdriver.Chrome(driver_path)
    driver.maximize_window()

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

            logger.info("Fetching user direct debits: {}".format(person_to_alert[0]))

            tbl_tr_ = '.clickable-table .debit-details'
            els_ = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, tbl_tr_)))

            # scan the table for Failed
            # break if Success or Written off appears first
            for row_ in range(1, len(els_) + 1):
                item = ".debit-details:nth-of-type({})".format(row_)
                el = driver.find_element_by_css_selector(item)
                line_= el.text.strip()
                logger.info(line_)
                if line_.count('Success') or line_.count('Written-Off') and cfg['test'].lower() != 'true':
                        break
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
                    logger.info('user added to alert list: {}'.format(person_to_alert))
                    break

            _navigate_to_customer_page()

    csv_ = _read_alerts()
    for prs_ in ppl_to_alert:
        for csv_alert in csv_:
            # user name and date
            # if match we dont send out
            if prs_[0] == csv_alert[0] and prs_[5] == csv_alert[5]:
                logger.info('Alert already sent: {} on: {}. Ignoring.'.format(prs_[0], csv_alert[5]))
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
            users_csv = [row for row in rd if row[1] != "Name"]
        for user_csv in users_csv:
            if user_csv[0] == name_ and user_csv[1] != '':
                logger.debug('Email found: {}  for user: {}'.format(user_csv[1], user_csv[0]))
                return user_csv[1]
        else:
            logger.debug('Email not found for: {}'.format(name_))
    except:
        logger.error('_get_email failed: ', exc_info=True)


def _text_message(text_recipient):
    logger.info('Texting: {}'.format(text_recipient))

    # recipient phone number
    phone_number = "+61" + text_recipient[2][1:]

    if cfg['test'].lower() == 'true':
        logger.debug('Intended recipient: {}'.format(phone_number))
        phone_number = cfg['twilio_to_test']
        logger.debug('Test mode, text recipient: {}'.format(phone_number))

    acc = cfg['twilio_account']
    token = cfg['twilio_token']
    from_number = cfg['twilio_from']
    text_content = cfg['text_content']

    try:
        client = TwilioRestClient(acc, token)

        message = client.messages.create(to=phone_number, from_=from_number,
                                         body=text_content)
        sid = message.sid
        body = client.messages.get(sid)
        status = body.status
        logger.info('Message sent to: {}, status: {}'.format(phone_number, status))
    except:
        logger.error('Text message failed to send to: {}'.format(phone_number), exc_info=True)


def _send_email(recipient):
    logger.debug('Emailing: {}'.format(recipient))

    # recipient
    name_recipient = recipient[0]
    email_recipient = recipient[6]

    if cfg['test'].lower() == 'true':
        logger.debug('Intended recipient: {}'.format(email_recipient))
        email_recipient = cfg['gmail_user']
        logger.debug('Test mode, email recipient: {}'.format(email_recipient))

    if not recipient:
        logger.info('Email not provided, not sent out to: {}'.format(name_recipient))
        return

    if cfg['gmail_method'] == 'less-secure':
        gmail_user = cfg['gmail_user']
        gmail_pwd = cfg['gmail_pwd']
        email_sender = cfg['gmail_user']
        email_subject = cfg['email_subject']
        email_content = cfg['email_content']

        message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (email_sender, email_recipient, email_subject, email_content)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(gmail_user, gmail_pwd)
            server.sendmail(email_sender, email_recipient, message)
            server.close()
            logger.info('Email sent to: {}'.format(email_recipient))
        except:
            logger.error('Email failed to send to: {}'.format(email_recipient), exc_info=True)


if __name__ == '__main__':
    verbose = None

    timestamp = time.strftime('%d%m%y', time.localtime())
    log_file = os.path.join(os.path.dirname(__file__), timestamp + ".log")
    file_hndlr = logging.FileHandler(log_file)
    logger.addHandler(file_hndlr)
    console = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(console)
    ch = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
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

    logger.info('Alert script started.')
    logger.debug('CLI args: {}'.format(opts))
    alert()
    driver.quit()