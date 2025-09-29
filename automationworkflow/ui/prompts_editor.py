import sys
from pathlib import Path
import streamlit as st

# Ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from prompts.loader import load_overrides, save_overrides


st.set_page_config(page_title="Prompt Editor", layout="wide")
st.title("Prompt Editor – Advanced")

st.markdown("Use this page to customize the system and user templates for Agents 2 and 3. Leave blank to use defaults.")

data = load_overrides()

c1, c2 = st.columns(2)
with c1:
    st.subheader("Agent 2 – System Prompt")
    a2_system = st.text_area("agent2.system", value=data.get("agent2.system", ""), height=220)
    st.subheader("Agent 2 – User Template")
    a2_user = st.text_area("agent2.user", value=data.get("agent2.user", ""), height=220)
with c2:
    st.subheader("Agent 3 – System Prompt")
    a3_system = st.text_area("agent3.system", value=data.get("agent3.system", ""), height=220)
    st.subheader("Agent 3 – User Template")
    a3_user = st.text_area("agent3.user", value=data.get("agent3.user", ""), height=220)

btns = st.columns(3)
if btns[0].button("Save changes"):
    data.update({
        "agent2.system": a2_system,
        "agent2.user": a2_user,
        "agent3.system": a3_system,
        "agent3.user": a3_user,
    })
    save_overrides(data)
    st.success("Saved.")
if btns[1].button("Reset to defaults"):
    save_overrides({})
    st.success("Cleared overrides. Using defaults.")
if btns[2].button("Reload"):
    st.experimental_rerun()


