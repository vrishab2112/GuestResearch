import os
import sys
import shutil
from pathlib import Path

import streamlit as st
import unicodedata
import re
import stat

# Ensure project root is on sys.path so imports work when running via Streamlit
# Use the project root (same level as in main app.py)
# __file__ is automationworkflow/ui/pages/Guests Manager.py → go up two levels to automationworkflow
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.title("Guests Manager")

outputs_root = PROJECT_ROOT / "outputs"
outputs_root.mkdir(parents=True, exist_ok=True)

guest_dirs = [d for d in outputs_root.iterdir() if d.is_dir()]
guest_names = sorted([d.name for d in guest_dirs])

def _normalize_name(name: str) -> str:
    # Normalize Unicode and collapse all whitespace to single ASCII spaces
    n = unicodedata.normalize("NFKC", name or "")
    n = re.sub(r"\s+", " ", n.strip())
    return n

if not guest_names:
    st.info("No guest outputs found yet. Run Agent 1 to create outputs.")
else:
    default_guest = st.session_state.get("selected_guest")
    try:
        default_index = guest_names.index(default_guest) if default_guest in guest_names else 0
    except Exception:
        default_index = 0

    selected = st.selectbox("Guest folders", guest_names, index=default_index)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Set as active guest"):
            st.session_state["selected_guest"] = selected
            st.success(f"Active guest set to: {selected}")

    with c2:
        with st.expander("Delete guest outputs (danger)"):
            st.warning("This will permanently delete all files for this guest under outputs.")
            st.caption("Type the exact guest folder name to confirm.")
            confirm = st.text_input("Confirm name", value="")
            delete_btn = st.button("Delete permanently", type="primary")
            if delete_btn:
                norm_selected = _normalize_name(selected)
                norm_confirm = _normalize_name(confirm)
                if not norm_confirm:
                    st.error("Please type the guest folder name to confirm.")
                elif norm_confirm != norm_selected:
                    # Try to find a directory whose normalized name matches what the user typed
                    match = None
                    for d in guest_dirs:
                        if _normalize_name(d.name) == norm_confirm:
                            match = d
                            break
                    if match is None:
                        st.error("Name does not match any guest folder. Copy/paste from the dropdown above.")
                    else:
                        # Use the matched folder
                        target = match
                        try:
                            target.resolve().relative_to(outputs_root.resolve())
                        except Exception:
                            st.error("Invalid target path.")
                        else:
                            try:
                                def on_rm_error(func, path, exc_info):
                                    try:
                                        os.chmod(path, stat.S_IWRITE)
                                    except Exception:
                                        pass
                                    func(path)
                                shutil.rmtree(target, onerror=on_rm_error)
                                if st.session_state.get("selected_guest") == selected:
                                    st.session_state["selected_guest"] = ""
                                st.success(f"Deleted: {target.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete: {e}")
                else:
                    target = outputs_root / selected
                    try:
                        target.resolve().relative_to(outputs_root.resolve())
                    except Exception:
                        st.error("Invalid target path.")
                    else:
                        try:
                            def on_rm_error(func, path, exc_info):
                                try:
                                    os.chmod(path, stat.S_IWRITE)
                                except Exception:
                                    pass
                                func(path)
                            shutil.rmtree(target, onerror=on_rm_error)
                            if st.session_state.get("selected_guest") == selected:
                                st.session_state["selected_guest"] = ""
                            st.success(f"Deleted: {selected}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")

    st.markdown("---")
    st.caption("Tip: After deletion, you can re-run Agents for the same name to rebuild clean outputs.")


