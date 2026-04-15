import json
import re


def print_all_majors(data):
    """Prints all majors (keys) of the course data."""
    for major in data.keys():
        print(major)


def print_all_classes_for_major(data, dept_name):
    """Prints all classes for a given major."""
    courses = data[dept_name]["courses"]
    for c in courses:
        print(c)


def print_clases_term_offered(data, dept_name, term):
    """Prints courses from a specific department that are offered in a given term.

    Args:
        data (dict): A dictionary containing the course catalog data.
        dept_name (str): The name of the department (e.g., "Statistics (STAT)")
        term (str): The term to search for (e.g., "F" for Fall, "W" for Winter)

    Example:
        >>> print_clases_term_offered(course_data, "Statistics (STAT)", "F")
        STAT 130: F, W, SP
        STAT 150: F
        STAT 217: F, W, SP, SU
    """
    term_pattern = r"Term Typically Offered:\s*([^P\n]+)"

    courses = data[dept_name]["courses"]
    for course_code, course_info in courses.items():
        match = re.search(term_pattern, course_info["prerequisites"])
        if not match:
            print(f"No terms found for {course_code}")
            continue
        terms = match.group(1)
        if term in terms:
            print(f"{course_code}: {terms}")


if __name__ == "__main__":
    with open("course_info.json", "r") as file:
        data = json.load(file)

    # print_all_majors(data)

    # print_all_classes_for_major(data, "Statistics (STAT)")

    # Get all classes offered in a department in a term (F = Fall)
    # print_clases_term_offered(data, "Statistics (STAT)", "F")
