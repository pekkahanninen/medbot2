import openai
import os
import streamlit as st
import re
import random
import base58

# Aseta OpenAI API-avain
# Haetaan OpenAI API-avain ympäristömuuttujasta
openai.api_key = os.getenv("OPENAI_API_KEY")

client = openai.Client(api_key=openai.api_key)  # Käytetään ympäristömuuttujaa

# Avainsana tentin aloittamiseen
REQUIRED_KEYWORD = "medtentti"

# Alustetaan session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "selected_field" not in st.session_state:
    st.session_state.selected_field = None
if "questions" not in st.session_state:
    st.session_state.questions = []
    st.session_state.correct_answers = []
    st.session_state.user_answers = {}
    st.session_state.short_answer_questions = []
    st.session_state.short_answer_responses = {}
    st.session_state.feedback = []
    st.session_state.submitted = False

# **1️⃣ Avainsana ennen tenttiä**
st.title("🩺 Lääketieteen tenttibotti testaukseen - GPT-4o/PH25/v2biol")
st.write("Tenttibotti on ulkoinen palvelu, se ei tallenna mitään mutta käytön rajaamiseksi on luotu avainsana")
st.write("Voit luoda tentin niin monta kertaa kuin haluat - tentin jälkeen saat koodin, jolla voit todistaa tehneesi tentin")

if not st.session_state.authenticated:
    user_keyword = st.text_input("Syötä avainsana:", type="password")
    if st.button("✅ Jatka"):
        if user_keyword == REQUIRED_KEYWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Virheellinen avainsana. Yritä uudelleen.")
    st.stop()

# **2️⃣ Erikoisalan valinta**
st.write("AI:n promptausta varten tarvitsen tarkemman alan kuvauksen - esim: Biolääketiede, Fysiologia tai jokin muu täsmennys")

if not st.session_state.selected_field:
    selected_field = st.text_input("Kirjoita lääketieteen alan tarkempi määritelmä:")
    if st.button("🎯 Aloita tentti") and selected_field:
        st.session_state.selected_field = selected_field
        st.rerun()
    st.stop()

# **3️⃣ Tenttikysymysten generointi**
def generate_questions():
    """Generoi 4 monivalintakysymystä ja 2 sanallista kysymystä valitun annetun lääketieteen tai biolääketieteen alan perusteella."""
    prompt = (
        f"Luo tentti biolääketieteen opiskelijoille. Tentti on aihealue on {st.session_state.selected_field} keskeiset kysymykset"
        "Kysymysten tulee kattaa tämän alan keskeiset aiheet, jotka ovat biolääketieteellisesti merkittäviä ja opetuksessa painotettuja."
        "Tentti sisältää 4 merkityksellistä monivalintakysymystä ja 2 lyhyen vastauksen sanallista kysymystä, jotka vaativat päättelyä. "
        "Vältä monivalintakysymyksissä vastakkaisia vaihtoehtoja."
        "Kysymysten tulee olla vaikeita ja vaatia syvällistä biolääketieteellistä perusosaamista. "
        "Vältä potilastapauksia - keskity alan perusosaamiseen."
        "Älä käytä triviaalien yksityiskohtien tai harvinaisten oireyhtymien kysymyksiä.\n\n"
### **Monivalintakysymysten lisävaatimukset:**  
        "Väärien vastausvaihtoehtojen tulee olla uskottavia: vältä liian ilmeisiä tai triviaaleja vaihtoehtoja. " 
        "Käytä harhaanjohtavia mutta todennäköisiä virhevaihtoehtoja"  
        "Kysymysten tulee mitata syvempää ymmärrystä eikä vain faktamuistia."  
### **Lyhyen vastauksen kysymysten lisävaatimukset:**  
        "Vaadi päättelyä ja syy-seuraussuhteiden ymmärtämistä. Keskity kysymyksissä alan ydinsisältöihin." 
        "Esitä vastaukseen vaadittavat taustatiedot kysymyksessä." 
        "Ole tarkka suomen kielen bio- ja lääketieteellisessä terminologiassa sekä hyvässä kieliasussa. Käytä selkeää ja luonnollista suomen kieltä. Käytä aina eurooppalaisia mittayksiköitä (esim. kg, mmol/l, °C) ja vältä amerikkalaisia yksiköitä tai vieraskielisiä termejä."
        "Käytä käypä hoito suosituksiin perustuvia ratkaisuja kliinisissä kysymyksissä. Tarkista, että kysymyksissä noudatetaan modernia käytäntöä ja juuri annettuja sääntöjä. Kerro, jos jokin kysymys rikkoo ohjeita"
        "Muotoile vastaus näin:\n\n"
        "1. Kysymys: [Kirjoita kysymysteksti tähän]\n"
        "   A) [Vaihtoehto 1]\n"
        "   B) [Vaihtoehto 2]\n"
        "   C) [Vaihtoehto 3]\n"
        "   D) [Vaihtoehto 4]\n"
        "   Oikea vastaus: [A, B, C tai D]\n\n"
        "5. Sanallinen kysymys: [Kliininen tapausesimerkki tai analyyttinen kysymys]\n"
        "6. Sanallinen kysymys: [Toinen syvällinen lääketieteellinen kysymys]"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_text = response.choices[0].message.content

    questions = []
    correct_answers = []
    short_answer_questions = []
    mcq_pattern = re.findall(r"\d+\.\s*Kysymys:\s*(.*?)(?:\n\s*A\))", raw_text, re.DOTALL)
    options_pattern = re.findall(r"A\)\s*(.*?)\n\s*B\)\s*(.*?)\n\s*C\)\s*(.*?)\n\s*D\)\s*(.*?)\n", raw_text)
    correct_pattern = re.findall(r"Oikea vastaus:\s*([A-D])", raw_text)
    short_answer_pattern = re.findall(r"\d+\.\s*Sanallinen kysymys:\s*(.*)", raw_text)

    for i, (question, options) in enumerate(zip(mcq_pattern, options_pattern)):
        formatted_options = {chr(65 + j): option.strip() for j, option in enumerate(options)}
        questions.append({"question": question.strip(), "options": formatted_options})
        correct_answers.append(correct_pattern[i].strip())

    short_answer_questions = [q.strip() for q in short_answer_pattern]

    return questions, correct_answers, short_answer_questions

# **4️⃣ Luo tentti -nappi**
st.write("### Luo tentti painamalla alla olevaa nappia.")

if st.button("📝 Luo tentti"):
    st.session_state.questions, st.session_state.correct_answers, st.session_state.short_answer_questions = generate_questions()
    st.session_state.feedback = []
    st.session_state.submitted = False
    st.rerun()

# **5️⃣ Näytä kysymykset heti tentin luonnin jälkeen**
if st.session_state.questions:
    st.write("## 📋 Tenttikysymykset 1p/oikea vastaus")
    for idx, q in enumerate(st.session_state.questions):
        st.markdown(f"**Kysymys {idx + 1}:** {q['question']}")
        answer_labels = [f"{key}) {value}" for key, value in q["options"].items()]
        selected_option = st.radio(f"Valitse vastaus kysymykseen {idx + 1}:", answer_labels, index=None, key=f"mcq_{idx}")
        st.session_state.user_answers[idx] = selected_option[0] if selected_option else None

    for idx, q in enumerate(st.session_state.short_answer_questions):
        st.write(f"## ✍ Sanallinen kysymys {idx + 1} (0-3p)")
        st.session_state.short_answer_responses[f"short_answer_{idx}"] = st.text_area(q, key=f"short_answer_{idx}")

def generate_exam_code(score):
    """ Luo opiskelijalle Excel-yhteensopivan tenttikoodin """
    random_part = random.randint(10000000, 99999999)  # 8-numeroinen satunnaisluku
    score_str = f"{score:02d}"  # Muutetaan arvosana 2-numeroiseksi (08, 10 jne.)
    
    raw_data = f"{random_part}{score_str}"  # Yhdistetään satunnaisosa ja arvosana
    checksum = int(raw_data) % 97  # Oikea MOD97-laskenta koko numerosta
    full_code = f"{raw_data}{checksum:02d}"  # Lisätään tarkistusluku kahdella numerolla

    return full_code  # Tämä voidaan suoraan käyttää Excelissä


# **6️⃣ Vastausten tarkistus**
st.write("Kun ole tehnyt tentin tarkista vastauksesi allaolevasta napista")

if st.button("✅ Tarkista vastaukset") and not st.session_state.submitted:
    review_prompt = "Analysoi seuraavat vastaukset ja anna yksityiskohtaiset perustelut:\n\n"

    for i in range(4):
        student_answer = st.session_state.user_answers.get(i, "Ei vastattu")
        correct_answer = st.session_state.correct_answers[i]
        student_answer_text = st.session_state.questions[i]["options"].get(student_answer, "Ei vastattu")
        correct_answer_text = st.session_state.questions[i]["options"].get(correct_answer, "Ei löydy")

        review_prompt += f"**Kysymys {i + 1}:** {st.session_state.questions[i]['question']}\n"
        review_prompt += f"📌 Opiskelijan vastaus: {student_answer} ({student_answer_text})\n"
        review_prompt += f"✅ Oikea vastaus: {correct_answer} ({correct_answer_text})\n"
        review_prompt += "Selitä lääketieteellisesti, miksi vastaus on oikein tai väärin.\n\n"

    for i in range(2):
        review_prompt += f"**Sanallinen kysymys {i + 1}:** {st.session_state.short_answer_questions[i]}\n"
        review_prompt += f"📌 Opiskelijan vastaus: {st.session_state.short_answer_responses.get(f'short_answer_{i}', 'Ei vastattu')}\n"
        review_prompt += "Pisteytä asteikolla 0–3, jos vastaus on tyhjä anna 0 pistettä, jos vastaus on osittain oikein anna 1-2 pistettä ja täysin oikeasta 3 pistettä. Ilmoita selvästi muodossa 'Pisteytys: X'. Perustele arviointi yksityiskohtaisesti hyvällä suomen kielellä.\n\n"
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": review_prompt}]
    )

    st.session_state.feedback = response.choices[0].message.content

    # **Pisteiden laskenta**
    mcq_score = sum(1 for i in range(4) if st.session_state.user_answers.get(i) == st.session_state.correct_answers[i])

    # **Parannettu regex, joka löytää nyt "Pisteytys: X"**
    short_answer_scores = re.findall(r"Pisteytys:\s*(\d)", st.session_state.feedback)

    # **Summataan löydetyt pisteet**
    short_answer_score = sum(int(score) for score in short_answer_scores if score.isdigit())

    # **Lasketaan kokonaispistemäärä**
    st.session_state.total_score = mcq_score + short_answer_score
    st.session_state.submitted = True

if st.session_state.feedback:
    st.markdown(f"### 📘 Tarkka vastausanalyysi:\n{st.session_state.feedback}")
    st.markdown(f"### 🏆 Pistemääräsi: {st.session_state.total_score} / 10")
    
# **Luo ja näytä opiskelijan henkilökohtainen tenttikoodi**
    exam_code = generate_exam_code(st.session_state.total_score)
    st.markdown(f"### 🔑 Tenttikoodisi: `{exam_code}`")
    st.write("Säilytä tämä koodi! Sen avulla voit todistaa suorittaneesi tentin.")
