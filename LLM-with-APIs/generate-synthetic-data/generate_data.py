import boto3
from typing import List, Literal
from datetime import date
from pydantic import BaseModel, Field
import instructor
import time

class Student(BaseModel):
  student_id: str = Field(description="Student ID in format STU followed by 6 digits")
  first_name: str = Field(description="Student's first name")
  last_name: str = Field(description="Student's last name")
  email: str = Field(description="Student email in format firstname.lastname@university.edu")
  date_of_birth: date = Field(description="Student's date of birth")
  enrollment_date: date = Field(description="Date when student enrolled")
  major: str = Field(description="Student's major field of study")
  year: Literal["Freshman", "Sophomore", "Junior", "Senior"] = Field(description="Student's academic year")
  gpa: float = Field(ge=2.0, le=4.0, description="Student's GPA between 2.0 and 4.0")
  credits_completed: int = Field(ge=0, le=150, description="Number of credits completed")
  status: Literal["Active", "Inactive", "Graduated"] = Field(description="Student's enrollment status")

class StudentList(BaseModel):
  students: List[Student] = Field(description="List of synthetic student records")

def create_bedrock_client():
  bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
  return instructor.from_bedrock(bedrock_client)

def generate_synthetic_students(num_students: int, retries: int = 0) -> StudentList:
  print("invoking llm, retries:", retries)
  client = create_bedrock_client()
  message = f"""
  Generate {num_students} realistic and diverse synthetic student records.

  Guidelines:
  - Use realistic names
  - Generate valid email addresses following the pattern firstname.lastname@university.edu
  - Ensure dates are logical (birth dates should make students 18-25 years old typically)
  - Enrollment dates should be recent but before current date
  - Match credits_completed with the student's year (Freshman: 0-30, Sophomore: 31-60, etc.)
  - Vary majors across different fields of study
  - Generate realistic GPAs with some variation
  """

  try:
    response = client.chat.completions.create(
      modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
      messages=[{"role": "user", "content": message}],
      max_tokens=2000,
      temperature=0.7,
      response_model=StudentList,
    )
    return response
  except Exception as e:
    if "(ThrottlingException)" in str(e) and retries < 3:
      time.sleep((retries + 1) * 8)
      return generate_synthetic_students(num_students, retries + 1)
    print(e)
    exit(1)


def main() -> None:
  student_data = generate_synthetic_students(num_students=5)
  json_output = student_data.model_dump_json(indent=2)
  with open("synthetic_students.json", "w") as f:
    f.write(json_output)
  print("Wrote synthetic_students.json")
  for student in student_data.students:
    print(f"Name: {student.first_name} {student.last_name}")

if __name__ == "__main__":
  main()
