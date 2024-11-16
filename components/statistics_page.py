import streamlit as st
import pandas as pd
from utils.database import load_study_progress, load_flashcards, load_all_notes
from utils.helpers import get_priority_icon
from utils.navigate import go_to_flashcard_page

def render_statistics_page():
    st.button("🔙 Quay lại", on_click=go_to_flashcard_page, key="back_to_view")
    st.title("📊 Thống kê")
    # Create two columns for the cards
    col1, col2 = st.columns(2)

    # Card 1: Total Flashcards
    total_flashcards = len(st.session_state.flashcards)
    with col1:
        st.button(
            f"{total_flashcards} thẻ",
            type="primary",
            use_container_width=True,
            disabled=True,
        )

    # Card 2: Total Notes
    all_notes = load_all_notes()
    total_notes = len(all_notes)
    with col2:
        st.button(
            f"{total_notes} ghi chú",
            type="primary",
            use_container_width=True,
            disabled=True,
        )

    
    st.divider()
    # Load study progress data
    study_progress_df = load_study_progress()
            
    if not study_progress_df.empty:
        st.markdown("### Tiến Độ Học Tập")

        # Convert 'date' column to datetime and set it as the index
        study_progress_df['date'] = pd.to_datetime(study_progress_df['date'])
        study_progress_df = study_progress_df.set_index('date')
        
        # Drop the 'id' column if it exists
        study_progress_df = study_progress_df.drop(columns=['id'], errors='ignore')
        study_progress_df = study_progress_df.drop(columns=['user_id'], errors='ignore')

        # Rename columns to desired labels
        study_progress_df = study_progress_df.rename(columns={
            'good_count': 'Quá dễ 😎',
            'normal_count': 'Hông chắc 🤔',
            'bad_count': 'Cái qq j z😱'
        })

        # Plot the renamed DataFrame with Streamlit's line chart
        st.line_chart(study_progress_df, color=["#73EC8B", "#FF6600", "#FF4545"])


    st.divider()
    # 1. Biểu đồ phân phối các flashcard theo trạng thái Gold Time
    st.markdown("### Phân phối thẻ")

    # Define a dictionary to count each status
    status_counts = {'🔴': 0, '🟠': 0, '🔵': 0, '🟢': 0}

    # Calculate the status counts by using get_priority_icon function
    for card in st.session_state.flashcards:
        icon = get_priority_icon(card['gold_time'])
        status_counts[icon] += 1

    # Map icons to meaningful labels for the chart
    status_labels = {
        '🔴': 'Quá hạn',
        '🟠': 'Sắp đến hạn',
        '🔵': 'Còn 1-2 ngày',
        '🟢': 'Còn thời gian'
    }

    # Convert counts to a DataFrame for visualization
    status_df = pd.DataFrame({
        'Trạng thái': [status_labels[icon] for icon in status_counts],
        'Số lượng': list(status_counts.values())
    }).set_index('Trạng thái')

    # Display the bar chart
    st.bar_chart(status_df)

    # 2. Biểu đồ số lượng ghi chú trên mỗi flashcard
    st.divider()
    st.markdown("### Số lượng Ghi chú")
    note_counts = {}
    for note in all_notes:
        flashcard_id = note['flashcard_id']
        note_counts[flashcard_id] = note_counts.get(flashcard_id, 0) + 1

    flashcard_ids = [card['id'] for card in st.session_state.flashcards]
    counts = [note_counts.get(flashcard_id, 0) for flashcard_id in flashcard_ids]
    words = [card['word'] for card in st.session_state.flashcards]

    # Tạo DataFrame cho biểu đồ
    note_counts_df = pd.DataFrame({
        'Flashcard': words,
        'Số lượng Ghi chú': counts
    })
    note_counts_df.set_index('Flashcard', inplace=True)

    # Hiển thị biểu đồ cột
    st.bar_chart(note_counts_df.head(20), horizontal=True)

    # Nút quay lại trang flashcard_view
    st.button("🔙 Quay lại", on_click=go_to_flashcard_page, key="back_to_view_statistics")


if __name__ == "__main__":
    render_statistics_page()