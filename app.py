import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io

# Кастомні стилі
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Open+Sans&display=swap');

        html, body, [class*="css"] {
            font-family: 'Open Sans', sans-serif;
        }

        .centered-title {
            text-align: center;
            font-family: 'Open Sans', sans-serif;
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 20px;
        }

        .stButton>button {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
        }

        .stDownloadButton>button {
            background-color: #3498db;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Центрований заголовок
st.markdown('<div class="centered-title">📄 Розпізнавання рахунків та актів</div>', unsafe_allow_html=True)
st.write("🔍 Завантаж PDF-файл з рахунками або актами, і я витягну ключові дані.")

# Завантаження файлу
uploaded_file = st.file_uploader("Завантаж PDF", type=["pdf"])

# Функція для витягування тексту з PDF
def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

# Функція для витягування ключових полів з тексту
def extract_invoice_data(text):
    data = []
    blocks = re.split(r"(Рахунок(?:\s+фактура)?\s*№|Акт\s*№)", text, flags=re.IGNORECASE)
    if len(blocks) < 3:
        return []

    for i in range(1, len(blocks), 2):
        doc_type = blocks[i].strip()
        content = blocks[i + 1]
        entry = {"Тип документа": doc_type}

        entry["Номер документа"] = re.search(r"№\s*([A-Za-zА-Яа-я0-9\-/]+)", content)
        entry["Дата"] = re.search(r"\b(?:від)?\s*(\d{1,2}[./]\d{1,2}[./]\d{2,4})", content)
        entry["Постачальник"] = re.search(r"(ТОВ|КП|КНП|ФОП|ПП|ПрАТ|АТ|ПРИВАТНЕ АКЦІОНЕРНЕ ТОВАРИСТВО)[^\n,]+", content, re.IGNORECASE)
        entry["ЄДРПОУ постачальника"] = re.search(r"(?:ЄДРПОУ|Код за ЄДРПОУ)\s*[:№]?\s*(\d{8})", content)
        entry["IBAN"] = re.search(r"UA[0-9A-Z]{25,29}", content)
        entry["МФО"] = re.search(r"МФО\s*[:№]?\s*(\d{6})", content)
        entry["Одержувач"] = re.search(r"(?:Одержувач|Покупець)[^\n:]*[:\s]*([^\n,]+)", content)
        entry["ЄДРПОУ одержувача"] = re.search(r"(?:ЄДРПОУ|Код за ЄДРПОУ).*?(\d{8})", content)
        entry["Договір"] = re.search(r"Договір[^\n:]*[:\s]*([^\n,]+)", content)
        entry["Сума без ПДВ"] = re.search(r"(?:Сума без ПДВ|Разом без ПДВ)[^\d]*(\d+[.,]?\d*)", content)
        entry["ПДВ"] = re.search(r"ПДВ[^\d]*(\d+[.,]?\d*)", content)
        entry["Сума з ПДВ"] = re.search(r"(?:Всього|Разом|Загальна сума з ПДВ)[^\d]*(\d+[.,]?\d*)", content)

        for key in entry:
            match = entry[key]
            if isinstance(match, re.Match) and match.lastindex:
                entry[key] = match.group(1).strip()
            else:
                entry[key] = None

        data.append(entry)

    return data

# Обробка файлу
if uploaded_file:
    with st.spinner("⏳ Обробка файлу..."):
        text = extract_text_from_pdf(uploaded_file)
        records = extract_invoice_data(text)

        if records:
            df = pd.DataFrame(records)
            st.success(f"✅ Знайдено документів: {len(df)}")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.dataframe(df.style.highlight_null())

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name="Документи")
                st.download_button(
                    label="⬇️ Завантажити Excel",
                    data=output.getvalue(),
                    file_name="розпізнані_документи.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with col2:
                st.markdown("### 🧾 JSON структура")
                st.json(records, expanded=False)

        else:
            st.warning("⚠️ Не вдалося знайти жодного рахунку або акту в документі.")
