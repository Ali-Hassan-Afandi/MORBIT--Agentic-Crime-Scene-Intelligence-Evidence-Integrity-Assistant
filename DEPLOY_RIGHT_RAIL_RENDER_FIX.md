# Right Rail Render Fix

The right progress rail was showing raw `<div>` markup because indented HTML inside
`st.markdown(..., unsafe_allow_html=True)` was being interpreted by Markdown as a code block.

This fix:
- keeps the right rail design unchanged,
- removes indentation/newline-sensitive markup from the progress rail,
- builds the rail HTML as one flush-left string,
- preserves desktop right rail and responsive bottom rail.

Deploy:
```bash
git add -A
git commit -m "Fix MORBIT right progress rail HTML rendering"
git pull --rebase origin main
git push origin main
```

Then reboot the Streamlit app once.
