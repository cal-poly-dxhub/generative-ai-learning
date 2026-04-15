import json
import re

import requests
from bs4 import BeautifulSoup


def valid_course_url(url):
    """Validates if a URL matches the Cal Poly course catalog pattern.

    The URL must:
    - Start with 'https://catalog.calpoly.edu/coursesaz/'
    - End with a department code in lowercase letters

    Args:
        url (str): The URL to validate

    Returns:
        bool: True if URL matches the pattern, False otherwise

    Examples:
        >>> valid_course_url('https://catalog.calpoly.edu/coursesaz/aged/')
        True
        >>> valid_course_url('https://catalog.calpoly.edu/coursesaz/')  # No department code
        False
        >>> valid_course_url('https://catalog.calpoly.edu/coursesaz/aged/something')  # Extra path
        False
    """
    pattern = r"^https://catalog\.calpoly\.edu/coursesaz/[a-z]+/$"
    return bool(re.match(pattern, url))


def fetch_and_extract_links(url):
    """Fetch HTML content from URL and extract all links

    Args:
        url (str): URL to fetch HTML from

    Returns:
        list: List of dictionaries containing link text and href
    """

    # Fetch the webpage
    response = requests.get(url)

    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all <a> tags (html url tags)
    links = soup.find_all("a")

    # Extract link text and href for each link
    link_data = []
    link_set = set()  # Used to ensure we don't grab duplicate links
    for link in links:
        href = link.get("href")
        text = link.get_text(strip=True)

        # Only include links that have both href and text
        if href and text:
            # Convert relative URLs to absolute URLs (basically just add the https://catalog.calpoly.edu back into the link)
            if href.startswith("/"):
                href = f"https://catalog.calpoly.edu{href}"

            # If the link is in format https://catalog.calpoly.edu/courseaz/course
            if valid_course_url(href):
                # If we have not already added this link
                if href not in link_set:
                    # Add link and link text to the list
                    link_data.append({"text": text, "href": href})
                link_set.add(href)

    return link_data


def get_major_classes(course_url):
    """Scrapes course information from a given Cal Poly course catalog URL.

    Args:
        course_url (str): The URL of the department's course catalog page
        http://catalog.calpoly.edu/coursesaz/course/

    Returns:
        dict: A nested dictionary containing course information in the format:
            {
                "Major Name": {
                    "courses": {
                        "COURSE 101": {
                            "name": "Course Name",
                            "units": "4 units",
                            "prerequisites": "Prerequisites info",
                            "description": "Course description"
                        },
                        ...
                    }
                }
            }

    Example:
        >>> url = "http://catalog.calpoly.edu/coursesaz/stat/"
        >>> data = get_major_classes(url)
    """
    # Fetch the webpage
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")
    courses_dict = {}

    # Get major name from the page title
    major_name = soup.find("h1").text.strip()

    # Find all course blocks
    course_blocks = soup.find_all("div", class_="courseblock")

    for block in course_blocks:
        # Get course title block
        title_block = block.find("p", class_="courseblocktitle").text.strip()

        # Extract course number and name
        course_info = title_block.split(".")
        course_number = course_info[0].strip()
        course_name = course_info[1].strip()

        # Get units
        units = block.find("span", class_="courseblockhours").text.strip()

        # Get course description
        description = block.find("div", class_="courseblockdesc")
        if description:
            description = description.text.strip()
        else:
            description = ""

        # Get prerequisites/corequisites if they exist
        extended = block.find("div", class_="courseextendedwrap")
        prereqs = ""
        if extended:
            prereqs = extended.text.strip()

        # Store course info under its course number
        courses_dict[course_number] = {
            "name": course_name,
            "units": units,
            "prerequisites": prereqs,
            "description": description,
        }

    # Create the final JSON structure
    json_structure = {major_name: {"courses": courses_dict}}

    return json_structure


# Example usage
if __name__ == "__main__":
    url = "https://catalog.calpoly.edu/coursesaz/"

    print("Fetching major listing...")
    links = fetch_and_extract_links(url)
    print("Major listing fetch complete")

    class_info = {}
    for link in links:
        print(f"Fetching: {link['text']} URL: {link['href']}")
        url = link["href"]
        major_classes = get_major_classes(url)

        # Combine major with all classes
        class_info.update(major_classes)

    # Print total number of links found
    print(f"\nTotal links found: {len(links)}")

    with open("course_info.json", "w") as file:
        file.write(json.dumps(class_info, indent=4))
