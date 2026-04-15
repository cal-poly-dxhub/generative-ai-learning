# Cal Poly Course Catalog Scraper

This project demonstrates how to scrape and extract course information from the Cal Poly course catalog website.

## Contact

**Instructor**: Nick Riley - njriley@calpoly.edu

## Video

[Click here to launch the lesson](https://csuai-summer-camp-public-content.s3.us-east-1.amazonaws.com/csuai_calpoly_webscraping_demo.mp4)
## What You'll Learn

- Web scraping with Python using BeautifulSoup
- Extracting structured data from HTML pages
- Processing and organizing course information
- Working with JSON data

## Getting Started

Follow these steps in order:

### 1. Clone the Repository

```bash
git clone https://github.com/cal-poly-dxhub/catalog-web-scraper.git
cd major_information_scraper
```

### 2. Create a Virtual Environment

For macOS/Linux:
```bash
python -m venv venv
source venv/bin/activate
```

For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Required Packages

```bash
pip install -r requirements.txt
```

### 4. Run the Web Downloader

```bash
python web_downloader.py
```

### 5. Run the Data Parser to view content
*Note: You can also view the data in the generated JSON file from step 4.*
```bash
python data_parser.py
```

This will:
1. Fetch all department links from the Cal Poly course catalog
2. Extract course information for each department
3. Save the results to a JSON file (course_info.json)

## Common Issues

- **Rate Limiting**: Be respectful of the website's resources by not making too many requests too quickly
- **HTML Structure Changes**: If the website structure changes, the scraper may need to be updated
- **Network Issues**: Ensure you have a stable internet connection
- **Missing Data**: Some courses may have incomplete information

## Learn More

- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Requests Library](https://docs.python-requests.org/en/latest/)
- [Web Scraping Best Practices](https://www.scrapehero.com/how-to-prevent-getting-blacklisted-while-scraping/)
