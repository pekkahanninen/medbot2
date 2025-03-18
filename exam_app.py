import streamlit as st
import os
from fpdf import FPDF
import io
from openai import OpenAI

# Luo OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Alusta session_state-muuttujat
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = ""
if "answers_submitted" not in st.session_state:
    st.session_state.answers_submitted = False
if "student_answers_mcq" not in st.session_state:
    st.session_state.student_answers_mcq = [""] * 4
if "student_answers_short" not in st.session_state:
    st.session_state.student_answers_short = ["", ""]
if "final_analysis" not in st.session_state:
    st.session_state.final_analysis = ""

# Sovelluksen otsikko
st.title("Lääketieteellinen kaksivaiheinen tenttisovellus")

st.markdown("### 1. Anna tentin aihealue ja opiskelijataso")

subject_area = st.text_input("Aihealue (esim. fysiologia, sisätaudit, genetiikka):")
student_level = st.text_input("Opiskelijataso (esim. 1. vuoden opiskelijat, kliinisen vaiheen opiskelijat):")

# Promptin rakennus
def build_exam_prompt(subject_area, student_level):
    return f"""
Luo tentti lääketieteen opiskelijoille. Tentti on suunnattu: {student_level}.
Aihealue on: {subject_area}.

Tentissä tulee olla:
- 4 monivalintakysymystä (kussakin neljä vaihtoehtoa A–D)
- 2 lyhyttä sanallista kysymystä, joissa opiskelija selittää mekanismeja, syy–seuraussuhteita tai kliinisiä päätöksiä

Kysymysten tulee perustua kyseisen alan keskeisiin ydinsisältöihin ja ajankohtaiseen tieteelliseen tietoon.
Jos aihealue kuuluu kliinisiin lääketieteen aloihin, huomioi Käypä hoito -suositukset mahdollisuuksien mukaan osana kysymysten sisältöä ja oikeita vastausperusteita.

Monivalintakysymysten tulee olla vaativia ja testata ymmärrystä ja päättelykykyä – ei pelkästään muistamista.
Vältä johtavia tai vastakkaisia vaihtoehtoja (esim. 'lisääntyy' vs. 'vähenee').

Sanallisten kysymysten vastaukset tulee pisteyttää asteikolla 0–3 pistettä. Älä sisällytä vielä oikeita vastauksia. Palauta vain kysymykset.
"""

def build_analysis_prompt(original_exam, mcq_answers, short_answers):
    return f"""
Tässä on opiskelijan vastaukset lääketieteen tenttiin.

Tenttikysymykset:
{original_exam}

Opiskelijan vastaukset:
Monivalintakysymykset:
1. {mcq_answers[0]}
2. {mcq_answers[1]}
3. {mcq_answers[2]}
4. {mcq_answers[3]}

Sanalliset kysymykset:
1. {short_answers[0]}
2. {short_answers[1]}

Tarkista vastaukset. Arvioi jokainen kysymys erikseen:
- Anna oikeat vastaukset
- Anna perusteet oikeille vastauksille
- Pisteytä sanalliset vastaukset asteikolla 0–3 pistettä per kysymys
- Laske kokonaispistemäärä asteikolla 0–10 pistettä (4 pistettä MCQ + 6 pistettä sanalliset)
"""

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split("\n"):
        pdf.multi_cell(0, 10, line)
    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# Luo tentti -painike
st.markdown("### 2. Luo tentti")

if st.button("Luo tentti"):
    if subject_area and student_level:
        with st.spinner("Tenttiä laaditaan..."):
            try:
                prompt = build_exam_prompt(subject_area, student_level)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}]
                )
                exam_text = response.choices[0].message.content
                st.session_state.exam_questions = exam_text
                st.session_state.answers_submitted = False
            except Exception as e:
                st.error(f"Tentin generointi epäonnistui: {e}")
    else:
        st.warning("Anna aihealue ja opiskelijataso ennen tentin luontia.")

# Näytä tentti ja lataus
if st.session_state.exam_questions:
    st.markdown("### Generoitu tentti:")
    st.markdown(st.session_state.exam_questions)

    st.download_button("Lataa tentti .txt", data=st.session_state.exam_questions, file_name="tentti.txt", mime="text/plain")
    pdf_bytes = create_pdf(st.session_state.exam_questions)
    st.download_button("Lataa tentti .pdf", data=pdf_bytes, file_name="tentti.pdf", mime="application/pdf")

    st.markdown("### 3. Opiskelijan vastaukset")

    for i in range(4):
        st.session_state.student_answers_mcq[i] = st.text_input(f"Monivalinta {i+1} vastaus (A–D):", value=st.session_state.student_answers_mcq[i])

    for i in range(2):
        st.session_state.student_answers_short[i] = st.text_area(f"Sanallinen vastaus {i+1}:", value=st.session_state.student_answers_short[i])

    if st.button("Tarkista vastaukset"):
        with st.spinner("Tarkistetaan vastauksia..."):
            try:
                analysis_prompt = build_analysis_prompt(
                    st.session_state.exam_questions,
                    st.session_state.student_answers_mcq,
                    st.session_state.student_answers_short
                )
                analysis_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": analysis_prompt}]
                )
                analysis_text = analysis_response.choices[0].message.content
                st.session_state.final_analysis = analysis_text
                st.session_state.answers_submitted = True
            except Exception as e:
                st.error(f"Vastausten tarkistus epäonnistui: {e}")

# Näytä vastausanalyysi
if st.session_state.answers_submitted:
    st.markdown("### Vastausanalyysi ja palaute:")
    st.markdown(st.session_state.final_analysis)

    st.download_button("Lataa analyysi .txt", data=st.session_state.final_analysis, file_name="vastausanalyysi.txt", mime="text/plain")
    pdf_analysis = create_pdf(st.session_state.final_analysis)
    st.download_button("Lataa analyysi .pdf", data=pdf_analysis, file_name="vastausanalyysi.pdf", mime="application/pdf")