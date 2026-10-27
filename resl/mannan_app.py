"""Optional Streamlit frontend; launch from the repository root.

python -m streamlit run resl/mannan_app.py --server.address 127.0.0.1
No trained model is loaded. Use made-up examples only.
"""
from resl.mannan_demo import EXAMPLES, OPTIONS, preview_application
from resl.mannan_preprocessing import NUMERIC, BOUNDS

def main():
    import streamlit as st
    st.set_page_config(page_title="RESL research preview", page_icon="🏠", layout="centered")
    st.caption("TEAM 2B · LOCAL RESEARCH PROTOTYPE")
    st.title("Application review preview")
    st.warning("Made-up applications only. No fitted model, risk estimate or lending decision.")
    st.write("Validate a synthetic application and inspect the input contract.")
    selected = st.selectbox("Start with an example", list(EXAMPLES))
    example = EXAMPLES[selected]
    with st.form("synthetic_application"):
        values = {}
        for field in NUMERIC:
            values[field] = st.text_input(field.replace("_", " ").title(),
                                          value=str(example[field]), key=selected + field)
        for field, options in OPTIONS.items():
            choices = sorted(options)
            values[field] = st.selectbox(field.replace("_", " ").title(), choices,
                                         index=choices.index(example[field]), key=selected + field)
        submitted = st.form_submit_button("Validate synthetic application")
    if submitted:
        try:
            result = preview_application(values)
        except ValueError as exc:
            st.error(str(exc))
            return
        st.metric("Risk band", result["band"])
        st.info(result["message"])
        if result["missing_fields"]:
            st.write("Missing fields:", ", ".join(result["missing_fields"]))
        st.subheader("Validated inputs")
        st.json(result["inputs"])
        st.caption(result["explanation"])
    with st.expander("Units and next integration step"):
        st.write("DTI, LTV and annual rate are percentages; original term is months. "
                 "Balance is the original currency amount, not a converted Canadian value.")
        st.write("Connect Hazim's reviewed model/input contract and Sweta's accepted bands "
                 "before displaying any model output. Do not paste real borrower information.")
        st.write("Offline fallback: python -m resl.mannan_demo")
    st.caption("Inputs are not written to files by this app. Run on localhost only.")

if __name__ == "__main__":
    main()
