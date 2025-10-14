# watch_together.py
import streamlit as st
import time

# 1️⃣ Page config must be first Streamlit command
st.set_page_config(page_title="🎬 Watch Together", layout="centered")

# ---------- Shared Room Data ----------
@st.cache_resource
def get_rooms():
    return {}

rooms = get_rooms()

# ---------- App UI ----------
st.title("🎥 Watch Together - YouTube Party")

room_id = st.text_input("Enter Room Name (e.g., friends-night):")
user_name = st.text_input("Your Name:")

if room_id and user_name:
    # Create room if it doesn't exist
    if room_id not in rooms:
        rooms[room_id] = {"video_url": "", "chat": []}

    room = rooms[room_id]

    # --- YouTube Link Section ---
    st.subheader("🎞 Paste YouTube Link")
    new_link = st.text_input("YouTube URL:", value=room["video_url"], key=f"url_{room_id}")

    if st.button("Update Link", key=f"update_{room_id}"):
        room["video_url"] = new_link
        st.success("✅ Video updated for everyone!")

    # --- Display Video ---
    if room["video_url"]:
        st.video(room["video_url"])

    # --- Chat Section ---
    st.subheader("💬 Group Chat")

    # Display previous messages
    for msg in room["chat"]:
        st.markdown(f"**{msg['user']}**: {msg['msg']}")

    # Send new message
    new_message = st.chat_input("Type your message...")
    if new_message:
        room["chat"].append({"user": user_name, "msg": new_message})
        st.experimental_rerun()  # Safe rerun only when a message is sent

    # --- Auto-refresh every 5 seconds ---
    # Use st.empty() + time.sleep + rerun
    refresh_container = st.empty()
    with refresh_container.container():
        time.sleep(5)
        st.experimental_rerun()
