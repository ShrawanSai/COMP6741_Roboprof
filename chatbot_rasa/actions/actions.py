
import requests
import json
import re

from rdflib import Graph, Literal, RDF, URIRef, Namespace, Dataset

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from langchain.llms import OpenAI
from langchain import PromptTemplate

def rewrite_with_llm(preface_text, answers):
    llm = OpenAI(model_name="gpt-3.5-turbo-instruct", openai_api_key='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')
    result_found = True
    if isinstance(answers, list):
        if len(answers) == 0:
            result_found = False
    if isinstance(answers, str ):
        if len(answers) == 0:
            result_found = False
    if not result_found:
        template = """
        description_of_answers: {preface_text}
        Looking at what the description_of_answers is saying, generate a message saying you could not find the requested information
        """
        
        prompt = PromptTemplate(
        
        input_variables=["preface_text"],
        
        template=template,
        )
        
        final_prompt = prompt.format(preface_text=preface_text,)
        return llm(final_prompt)
        
    try:
        template = """
        description_of_answers: {preface_text}
        answers = {answers}
        Based on the description_of_answers, formulate the answers for the user to read and understand in a human-readable manner. Do not add any new information. Make sure you convey the whole of the answers. If answers is long, consider using a list. 
        If there is a path in the answers, make sure to include the full paths in your response
        If answers is empty, then make a message that says you are sorry and could not find what was asked in the description_of_answers. Do not give any more information
        """
        
        prompt = PromptTemplate(
        
        input_variables=["preface_text", "answers"],
        
        template=template,
        )
        
        final_prompt = prompt.format(preface_text=preface_text, answers = answers )
    
        return llm(final_prompt)
    except Exception as e:
        if isinstance(answers, list):
            return_message = f"{preface_text} \n"
            for i in answers:
                return_message += str(i) + "\n"
        else:
            return_message = f"{preface_text} \n {answers}"
        return return_message
            


def make_fuseki_server_request(sparql_query):
    # Define the endpoint URL
    endpoint_url = 'http://localhost:3030/intelligent_systems/sparql'

    # Define the payload
    payload = {'query': sparql_query}

    # Send the POST request
    response = requests.post(endpoint_url, data=payload)
    return response


# Q1) List all courses offered by the [university]
class CoursesOfferedbyUni(Action):

    def name(self) -> Text:
        return "action_courses_offeredby_uni"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        university = tracker.slots['university']

        if "concordia" in university.lower() or "university" in university.lower():
            university = "Concordia University"

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT ?courseName ?courseSubject ?courseNumber
            WHERE {{
        
            ?university rdf:type acad:University ;
                    acad:universityName ?universityName ;
                    acad:offers ?course .
                    FILTER (?universityName = "{university}") 
        
            ?course rdf:type vivo:Course ;
                    acad:courseName ?courseName ;
                    acad:courseSubject ?courseSubject ;
                    acad:courseNumber ?courseNumber .
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        course_info = []
        for course in y:
            course_name = course['courseName']['value']
            course_subject = course['courseSubject']['value']
            course_number = course['courseNumber']['value']
            course_info.append([course_name, course_subject, course_number])

        response = rewrite_with_llm(f"Here are the courses offered by {university}: \n", course_info)

        dispatcher.utter_message(response)

# Q3) Which [topics] are covered in [course] during [lecture number]?
class TopicsCoveredByCourseInLecture(Action):

    def name(self) -> Text:
        return "action_topics_coveredby_course_in_lecturenumber"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_name = tracker.slots['course']
        
        lecture_number = tracker.slots['lectureNumber']
        print(lecture_number)
        lecture_number = re.search(r'\d+', lecture_number).group()
        print(lecture_number)
        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT DISTINCT ?topicName
            WHERE {{
        
            ?course rdf:type vivo:Course ;
                    acad:courseName "{course_name}" ;
                    acad:hasLecture ?lecture.
            ?lecture rdf:type acad:Lecture ;
                    acad:lectureNumber ?lectureNumber .
                    FILTER (?lectureNumber = {lecture_number})
            ?topic rdf:type acad:Topic ;
                    acad:hasProvenanceInformation ?lecture ;
                    acad:topicName ?topicName           
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        topic_info = []
        for topic in y:
            topic_name = topic['topicName']['value']
            topic_info.append(topic_name)

        response = rewrite_with_llm(f"The topics covered in {course_name} during lecture {lecture_number} are: \n", topic_info)
        dispatcher.utter_message(response)

# Q4) List all [courses] offered by [university] within the [subject] (e.g., \COMP", \SOEN").
class CoursesOfferedbyUniWithinCourse(Action):

    def name(self) -> Text:
        return "action_courses_offeredby_uni_within_course"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        university_name = tracker.slots['university']

        if "concordia" in university_name.lower() or "university" in university_name.lower():
            university = "Concordia University"
        
        course_subject1 = tracker.slots['courseSubject']

        
        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT ?courseName ?courseSubject ?courseNumber
            WHERE {{
        
            ?university rdf:type acad:University ;
                    acad:universityName ?universityName ;
                    acad:offers ?course .
                    FILTER (?universityName = "{university_name}") 
        
            ?course rdf:type vivo:Course ;
                    acad:courseName ?courseName ;
                    acad:courseNumber ?courseNumber ;
                    acad:courseSubject ?courseSubject ;
                    FILTER (?courseSubject = "{course_subject1}") 
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        course_info = []
        for course in y:
            course_name = course['courseName']['value']
            course_subject = course['courseSubject']['value']
            course_number = course['courseNumber']['value']
            course_info.append([course_name, course_subject, course_number])
        
        response = rewrite_with_llm(f"Here are the courses covered in {university_name} for the subject {course_subject1}: \n", course_info)

        dispatcher.utter_message(response)

# Q5) What [materials] (slides, readings) are recommended for [topic] in [course] [number]?
class MaterialsRecommendedForTopicInCourse(Action):

    def name(self) -> Text:
        return "action_materials_recommendation_for_topic_in_coursenumber"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        topic_name = tracker.slots['topic']
        course_number = tracker.slots['courseNumber']

        sparql_query = f"""
        PREFIX ac: <http://umbel.org/umbel/ac/>
        PREFIX prefix: <http://prefix.cc/>
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT DISTINCT ?content ?class 
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject .
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 

        ?lecture rdf:type acad:Lecture ;
                acad:hasContent ?content .
        
        ?content a ?class .
        FILTER (?class = acad:Slides || ?class = acad:Reading)
        ?topic rdf:type acad:Topic ;
                acad:topicName "{topic_name}" ;
                acad:hasProvenanceInformation ?lecture .
        }}
        """

        response = make_fuseki_server_request(sparql_query)
        material_info = []

        y = json.loads(response.text)
        y = y['results']['bindings']
        material_info = []
        for item in y:
            content = item['content']['value']
            material_class = item['class']['value'].split('#')[1]
            material_info.append((content, material_class))

        response = rewrite_with_llm(f"The materials recommended for {topic_name} in {course_subject} {course_number} are: \n", material_info)

        dispatcher.utter_message(response)

# Q6) How many credits is [course] [number] worth?
class CreditsWorthOfCourse(Action):

    def name(self) -> Text:
        return "action_credits_for_course"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']

        sparql_query = f"""
        PREFIX ac: <http://umbel.org/umbel/ac/>
        PREFIX prefix: <http://prefix.cc/>
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT DISTINCT ?courseCredits
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject ;
                acad:courseCredits ?courseCredits
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        course_credits = []
        for course in y:
            course_credits = course['courseCredits']['value']

        response = rewrite_with_llm(f"The number of credits awarded for completing {course_subject} {course_number} is: \n", course_credits)

        dispatcher.utter_message(response)

# Q7) For [course] [number], what additional resources (links to web pages) are available
class AdditionalResourcesForCourse(Action):

    def name(self) -> Text:
        return "action_additional_resources_for_course"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT DISTINCT ?courseWebpage ?lectureLink ?topicLink
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject ;
                acad:courseWebpage ?courseWebpage ;
                acad:coversTopic ?topic ;
                acad:hasLecture ?lecture .
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        ?lecture rdf:type acad:Lecture ;
                acad:lectureLink ?lectureLink .
        ?topic rdf:type acad:Topic ;
                acad:hasTopicLink ?topicLink
        
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        additional_resources = []
        for item in y:
            course_webpage = item['courseWebpage']['value']
            lecture_link = item['lectureLink']['value']
            topic_link = item['topicLink']['value']
            additional_resources.append(course_webpage)
            additional_resources.append(lecture_link)
            additional_resources.append(topic_link)

        # Remove duplicates from the list
        additional_resources = list(set(additional_resources))
        
        response = rewrite_with_llm(f"Additional resources for {course_subject} {course_number} are: \n", additional_resources)

        dispatcher.utter_message(response)

# Q8) Detail the content (slides, worksheets, readings) available for [lecture number] in [course] [number].
class ContentAvailableForLectureInCourse(Action):

    def name(self) -> Text:
        return "action_content_for_course_in_lecturenumber"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']
        lecture_number = tracker.slots['lectureNumber']
        lecture_number = re.search(r'\d+', lecture_number).group()

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT DISTINCT ?content
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject .
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        ?lecture rdf:type acad:Lecture ;
                acad:hasContent ?content ;
                acad:lectureNumber ?lectureNumber .
                FILTER (?lectureNumber = {lecture_number})
            ?content a ?class .
        FILTER (?class = acad:Slides || ?class = acad:Reading || ?class = acad:Worksheet)
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)
        content_info = [item['content']['value'] for item in y['results']['bindings']]

        response = rewrite_with_llm(f"The content available for lecture {lecture_number} in {course_subject} {course_number} is: \n", content_info)
        
        dispatcher.utter_message(response)  

# Q10) What competencies [topics] does a student gain after completing [course] [number]?
class CompetenciesGainedForCourse(Action):

    def name(self) -> Text:
        return "action_competencies_after_course_completion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT DISTINCT ?topicName 
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject .
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        
        ?topic rdf:type acad:Topic ;
                acad:topicName ?topicName .
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        competency_info = []
        for competency in y:
            competency_name = competency['topicName']['value']
            competency_info.append(competency_name)

        response = rewrite_with_llm(f"The competencies gained after completing {course_subject} {course_number} are: \n", competency_info)

        dispatcher.utter_message(response)

# Q11) What grades did [student] achieve in [course] [number]?
class GradesAchievedForStudentInCourse(Action):

    def name(self) -> Text:
        return "action_grades_for_student_in_course"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        student_id = tracker.slots['studentID']
        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT ?courseGrade 
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject .
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        
        ?student rdf:type acad:Student ;
                acad:studentID ?studentID ;
                acad:completedCourse ?courseCompletion .
                FILTER (?studentID = "{student_id}")
        
        ?courseCompletion rdf:type acad:CompletedCourse ;
                acad:hasCourse ?course ;
                acad:courseGradeSemester ?courseGradeSemesterPair .
        
        ?courseGradeSemesterPair rdf:type acad:GradeSemesterPair ;
                            acad:courseGrade ?courseGrade .
        }}

        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        grades_info = []
        for grade in y:
            grade_value = grade['courseGrade']['value']
            grades_info.append(grade_value)

        response = rewrite_with_llm(f"The grades achieved by {student_id} in {course_subject} {course_number} are: \n", grades_info)

        dispatcher.utter_message(response)

# Q12) Which [students] have completed [course] [number]?
class StudentsCompletedCourse(Action):

    def name(self) -> Text:
        return "action_students_completed_course"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT ?studentID ?studentName
        WHERE {{
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseSubject ?courseSubject .
                FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        
        ?student rdf:type acad:Student ;
                acad:studentID ?studentID ;
                acad:studentName ?studentName ;
                acad:completedCourse ?courseCompletion .
        
        ?courseCompletion rdf:type acad:CompletedCourse ;
                acad:hasCourse ?course .
        }}

        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        students_info = []
        for student in y:
            students_info.append([student['studentID']['value'], student['studentName']['value']])

        response = rewrite_with_llm(f"The students who have completed {course_subject} {course_number} are: \n", students_info)

        dispatcher.utter_message(response)

# Q13) Print a transcript for a [student], listing all the course taken with their grades
class TranscriptForStudent(Action):

    def name(self) -> Text:
        return "action_transcript_for_student"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        student_id = tracker.slots['studentID']

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>

        SELECT DISTINCT ?courseSubject ?courseNumber ?courseName ?courseGrade ?courseSemester
        WHERE {{
        ?student rdf:type acad:Student ;
                acad:studentID ?studentID .
        FILTER (?studentID = "{student_id}")

        ?student acad:completedCourse ?courseCompletion .
        
        ?courseCompletion rdf:type acad:CompletedCourse ;
                            acad:hasCourse ?course ;
                            acad:courseGradeSemester ?courseGradeSemesterPair .
        
        ?courseGradeSemesterPair rdf:type acad:GradeSemesterPair ;
                            acad:courseGrade ?courseGrade ;
                            acad:courseSemester ?courseSemester .


        
        ?course rdf:type vivo:Course ;
                acad:courseNumber ?courseNumber ;
                acad:courseName ?courseName ;
                acad:courseSubject ?courseSubject .
        }}

        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        transcript_info = []
        for course in y:
            for course in y:
                course_subject = course['courseSubject']['value']
                course_number = course['courseNumber']['value']
                course_grade = course['courseGrade']['value']
                course_semester = "Course taken in Semester: " + course['courseSemester']['value']
                transcript_info.append([course_subject, course_number, course_grade, course_semester])
        
        response = rewrite_with_llm(f"The transcript for {student_id} is: \n", transcript_info)

        dispatcher.utter_message(response)

# Q2-1) What is the <course> about?
class CourseDescription(Action):

    def name(self) -> Text:
        return "action_about_course"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']


        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT ?courseDescription
            WHERE {{
        
            ?course rdf:type vivo:Course ;
                        acad:courseNumber ?courseNumber ;
                        acad:courseSubject ?courseSubject ;
                        acad:courseDescription ?courseDescription
                        FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}") 
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        course_description = []
        for course in y:
            course_description = course['courseDescription']['value']

        response = rewrite_with_llm(f"The course {course_subject} {course_number} is about: \n", course_description)

        dispatcher.utter_message(response)

# Q2-2) “Which topics are covered in event of course?
class TopicsCoveredByCourseEvent(Action):

    def name(self) -> Text:
        return "action_about_course_lecture_topics"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        course_subject = tracker.slots['courseSubject']
        course_number = tracker.slots['courseNumber']
        
        lecture_number = tracker.slots['lectureNumber']
        lecture_number = re.search(r'\d+', lecture_number).group()
        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT DISTINCT ?topicName
            WHERE {{
        
            ?course rdf:type vivo:Course ;
                    acad:courseNumber ?courseNumber ;
                    acad:courseSubject ?courseSubject ;
                    acad:hasLecture ?lecture.
                    FILTER (?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}")
            ?lecture rdf:type acad:Lecture ;
                    acad:lectureNumber ?lectureNumber .
                    FILTER (?lectureNumber = {lecture_number})
            ?topic rdf:type acad:Topic ;
                    acad:hasProvenanceInformation ?lecture ;
                    acad:topicName ?topicName           
        }}
        """

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        topic_info = []
        for topic in y:
            topic_name = topic['topicName']['value']
            topic_info.append(topic_name)

        response = rewrite_with_llm(f"The topics covered in {course_subject} {course_number} during lecture {lecture_number} are: \n ", topic_info)

        dispatcher.utter_message(response)

# Q2-3) Which course events cover <Topic>?
class CourseEventsCoveringTopic(Action):

    def name(self) -> Text:
        return "action_about_course_topic"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        topic_name = tracker.slots['topic']

        sparql_query = f"""
        PREFIX vivo: <http://vivoweb.org/ontology/core#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX acad: <http://acad.io/schema#>
        SELECT ?courseName ?courseSubject ?courseNumber ?lectureName ?lectureNumber
            WHERE {{
        
            ?course rdf:type vivo:Course ;
                        acad:courseNumber ?courseNumber ;
                        acad:courseSubject ?courseSubject ;
                        acad:courseName ?courseName ;
                        acad:hasLecture ?lecture.
            ?lecture rdf:type acad:Lecture ;
                    acad:lectureNumber ?lectureNumber ;
                    acad:lectureName ?lectureName .
            ?topic rdf:type acad:Topic ;
                            acad:hasProvenanceInformation ?lecture ;
                            acad:topicName ?topicName .
        FILTER(?topicName = "{topic_name}")
        }}
        """
        print(sparql_query)

        response = make_fuseki_server_request(sparql_query)

        y = json.loads(response.text)

        y = y['results']['bindings']

        events = []
        for course in y:
            course_name = "Course Name: " + str(course['courseName']['value'])
            course_subject = "Course Subject: " + course['courseSubject']['value']
            course_number = "Course Number: " + course['courseNumber']['value']
            lecture_name = "Lecture Name: " + course['lectureName']['value']
            lecture_number = "Lecture Number: " + course['lectureNumber']['value']
            events.append([course_name, course_subject, course_number, lecture_number, lecture_name])

    
        response = rewrite_with_llm(f"The course events covering {topic_name} are: \n ",events)

        dispatcher.utter_message(response)

