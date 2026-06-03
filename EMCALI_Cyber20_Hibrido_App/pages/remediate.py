from __future__ import annotations
import streamlit as st
from core.analysis import build_validation_script


def render():
    st.title('Remediación')
    df = st.session_state.findings_df
    selected_id = st.selectbox('Seleccione hallazgo para plan de tratamiento', df['finding_id'].tolist())
    row = df[df['finding_id'] == selected_id].iloc[0]
    st.write('**Recomendación base:**', row['recommendation'])
    st.markdown('''
1. Validar autorización de cambio.
2. Ejecutar remediación en ventana aprobada.
3. Verificar servicio y dependencia asociada.
4. Reescanear y cerrar evidencia.
''')
    script = build_validation_script(row)
    st.code(script, language='powershell' if 'Get-' in script else 'bash')
    st.download_button('Descargar script', script, file_name=f'validacion_{selected_id}.txt')
