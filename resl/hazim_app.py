"""Local synthetic forest demo. Never load a real-loan model in this preview."""
from pathlib import Path
import json
from resl.mannan_demo import EXAMPLES
from resl.mannan_preprocessing import NUMERIC
from resl.hazim_contract import CATEGORIES, validate_application
from resl.hazim_bundle import load_bundle

def demo_prediction(bundle, values):
    if bundle.payload["synthetic"] is not True:
        raise ValueError("This preview accepts only synthetic-trained packages")
    return bundle.predict(values)

def main():
    import streamlit as st
    st.set_page_config(page_title="RESL synthetic model demo", page_icon="🧪")
    st.caption("TEAM 2B | LOCAL SOFTWARE DEMONSTRATION")
    st.title("Synthetic forest preview")
    st.warning("Invented training data and applications only. These scores do not estimate real mortgage risk.")
    folder = Path(__file__).resolve().parents[1] / "models" / "hazim"
    bundle = None
    try:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        bundle = load_bundle(folder / "forest.json", expected_hash=manifest["model_hash"])
        if bundle.payload["synthetic"] is not True:
            raise ValueError("This preview accepts only synthetic-trained packages")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.info("Synthetic package unavailable. Run python -m resl.hazim_training --synthetic.")
        st.caption(str(exc))
    selected = st.selectbox("Start with an example", list(EXAMPLES))
    example = EXAMPLES[selected]
    with st.form("synthetic_forest_application"):
        values = {f: st.text_input(f.replace("_", " ").title(), str(example[f]), key=selected + f)
                  for f in NUMERIC}
        for field, options in CATEGORIES.items():
            choices = list(options)
            values[field] = st.selectbox(field.replace("_", " ").title(), choices,
                                         index=choices.index(example[field]), key=selected + field)
        submitted = st.form_submit_button("Run synthetic model")
    if submitted:
        try:
            clean = validate_application(values)
            if bundle is None:
                st.metric("Model status", "Unscored")
            else:
                result = demo_prediction(bundle, clean)
                st.metric("Synthetic model output", f'{result["probability"]:.3f}')
                st.info(result["band"] + ". Accepted risk bands remain pending.")
                if result["missing_fields"]:
                    st.write("Imputed missing fields:", ", ".join(result["missing_fields"]))
            st.json(clean)
        except (ValueError, OverflowError) as exc:
            st.error(str(exc))
    st.caption("No lending decision. Input summaries are not causal explanations or feature contributions. "
               "Inputs are not saved by the application. Run on localhost.")

if __name__ == "__main__":
    main()
