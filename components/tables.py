from __future__ import annotations

import pandas as pd
import streamlit as st


def show_table(rows: list[dict], title: str) -> None:
    st.subheader(title)
    if not rows:
        st.info("Nothing here yet.")
        return
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
