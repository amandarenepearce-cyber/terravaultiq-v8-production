from __future__ import annotations

import json

import streamlit as st

from core.storage import list_audiences, save_export_record
from modules.activation_studio.generator import build_activation_payload, make_activation_zip


def render(user: dict, project: dict | None) -> None:
    st.title("Activation Studio")
    if not project:
        st.info("Choose or create a project first.")
        return

    audiences = list_audiences(project["project_id"])
    if not audiences:
        st.info("Build an audience first so Activation Studio has something to package.")
        return

    selected = st.selectbox("Audience to activate", audiences, format_func=lambda x: x.get("campaign_name") or x.get("audience_name", "Unnamed audience"))

    default_offer = selected.get("offer") or "Get a better website that turns local homeowners into booked estimates and calls."
    offer = st.text_area("Offer / promise", value=default_offer, height=90)

    payload = build_activation_payload(project, selected, offer)

    st.subheader("Campaign brief")
    st.json({
        "brand": payload["brand"],
        "campaign": payload["campaign"],
        "audience": payload["audiences"][0],
        "recommended_launch_order": payload["recommended_launch_order"],
    })

    st.subheader("Generated assets")
    st.write(f"Copy variants: **{len(payload['assets']['copy_variants'])}**")
    st.write(f"Display sizes: **{', '.join(payload['display_sizes'])}**")
    st.write("Includes campaign brief, angle map, ad-copy CSV, creative prompts, display ads, persona map, objection bank, landing-page sync, testing matrix, test tree, and app-ready JSON.")

    zip_bytes, zip_name, final_payload = make_activation_zip(project, selected, offer)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download full activation ZIP",
            data=zip_bytes,
            file_name=zip_name,
            mime="application/zip",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download ad-studio-input JSON",
            data=json.dumps(final_payload, indent=2),
            file_name=f"activation_{selected['audience_id']}.json",
            mime="application/json",
            use_container_width=True,
        )

    if st.button("Save activation export record"):
        save_export_record({
            "export_id": f"activation_{selected['audience_id']}",
            "project_id": project["project_id"],
            "audience_id": selected["audience_id"],
            "type": "activation_package",
            "file_name": zip_name,
            "generated_at": final_payload["generated_at"],
            "summary": {
                "brand": final_payload["brand"],
                "campaign": final_payload["campaign"]["name"],
                "copy_variants": len(final_payload["assets"]["copy_variants"]),
                "display_sizes": final_payload["display_sizes"],
            },
        })
        st.success("Activation export record saved.")

    with st.expander("Preview full activation payload"):
        st.json(final_payload)
