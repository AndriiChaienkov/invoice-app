
import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io

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

    # Розбиваємо текст на блоки за рахунками/актами
    blocks = re.split(r"(Рахунок\s*№|Акт\s*№)", text, flags=re.IGNORECASE)
    if len(blocks) < 3:
        return []

    # Обробляємо кожен блок
    for i in range(1, len(blocks), 2):
        doc_type = blocks[i].strip()
        content = blocks[i + 1]

        entry = {"Тип документа": doc_type}

        # Витягуємо ключові поля
        entry["Номер документа"] = re.search(r"№\s*([A-Za-zА-Яа-я0-9\-/]+)", content)
        entry["Дата"] = re.search(r"від\s*(\d{1,2}[./]\d{1,2}[./]\d{2,4})", content)
        entry["Постачальник"] = re.search(r"(ТОВ|КП|КНП|ФОП|ПП|ПрАТ|АТ)[^\n,]+", content)
        entry["ЄДРПОУ постачальника"] = re.search(r"ЄДРПОУ\s*[:№]?\s*(\d{8})", content)
        entry["IBAN"] = re.search(r"UA[0-9A-Z]{25,29}", content)
        entry["МФО"] = re.search(r"МФО\s*[:№]?\s*(\d{6})", content)
        entry["Одержувач"] = re.search(r"Одержувач[^\n:]*[:\s]*([^\n,]+)", content)
        entry["ЄДРПОУ одержувача"] = re.search(r"ЄДРПОУ.*?(\d{8})", content)
        entry["Договір"] = re.search(r"Договір[^\n:]*[:\s]*([^\n,]+)", content)
        entry["Сума без ПДВ"] = re.search(r"Сума без ПДВ[^\d]*(\d+[.,]?\d*)", content)
        entry["ПДВ"] = re.search(r"ПДВ[^\d]*(\d+[.,]?\d*)", content)
        entry["Сума з ПДВ"] = re.search(r"(Всього|Разом).*?(\d+[.,]?\d*)", content)

        # Очищення результатів
        for key in entry:
            if isinstance(entry[key], re.Match):
                entry[key] = entry[key].group(1).strip()

        data.append(entry)

    return data

# Інтерфейс Streamlit
st.title("📄 Розпізнавання рахунків та актів")
st.write("Завантаж PDF-файл з рахунками або актами, і я витягну ключові дані.")

uploaded_file = st.file_uploader("Завантаж PDF", type=["pdf"])

if uploaded_file:
    with st.spinner("Обробка файлу..."):
        text = extract_text_from_pdf(uploaded_file)
        records = extract_invoice_data(text)

        if records:
            df = pd.DataFrame(records)
            st.success(f"✅ Знайдено документів: {len(df)}")
            st.dataframe(df)

            # Завантаження Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name="Документи")
            st.download_button(
                label="⬇️ Завантажити Excel",
                data=output.getvalue(),
                file_name="розпізнані_документи.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Не вдалося знайти жодного рахунку або акту в документі.")
