"""Admin-only Setup section. Downloads are never described as NAS receipts."""
from datetime import date

from modules.season_backup import BackupError, DESTINATION, create_backup, prerequisites


def render_season_backup(st):
    from auth import require_admin
    from portal_access import uses_supabase_auth, is_restore_test

    require_admin()
    st.header("Backup ved sæsonafslutning")
    st.write("Opret en samlet ZIP-fil med database, struktur, roller og dokumenter. "
             "Backuppen omfatter alle sæsoner. Tag gerne en kopi både før og efter sæsonafslutning.")
    st.caption(f"Gem den downloadede ZIP-fil i {DESTINATION}, og kontrollér derefter, at den findes på NAS’en.")
    if uses_supabase_auth() or is_restore_test():
        st.info("Backup er ikke aktiveret i testmiljøet.")
        return
    missing = prerequisites(st.secrets)
    if missing:
        st.info("Backup er forberedt, men skal konfigureres, før den kan bruges.")
        with st.expander("Manglende opsætning"):
            for item in missing:
                st.write("• " + item)
            st.write("Se supabase/BACKUP.md i projektet. Adgangskoder indtastes kun i Streamlit Secrets.")
        return
    year = st.number_input("Sæson på backupfilens navn", min_value=2025, max_value=2100,
                           value=date.today().year, step=1, key="backup_year")
    phase = st.selectbox("Tidspunkt", ["Før sæsonafslutning", "Efter sæsonafslutning"], key="backup_phase")
    quiet = st.checkbox("Ingen ændrer bookinger, opsætning eller dokumenter, mens backuppen oprettes",
                        key="backup_quiet")
    if st.button("Opret backup", disabled=not quiet, key="create_season_backup"):
        st.session_state.pop("season_backup_download", None)
        require_admin()
        stage = "Opretter forbindelse til Supabase"
        try:
            from supabase import create_client
            client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_BACKUP_KEY"])
            with st.status("Opretter backup …", expanded=True) as status:
                def report_progress(message):
                    nonlocal stage
                    stage = message
                    status.write(message)

                result = create_backup(st.secrets, client, year,
                                       "foer" if phase.startswith("Før") else "efter", report_progress)
                status.update(label="Backupfil kontrolleret og klar til download", state="complete")
            st.session_state["season_backup_download"] = result
        except BackupError as error:
            st.error(str(error))
        except Exception:
            st.error(f"Backuppen stoppede ved: {stage}. "
                     "Ingen ny backup er frigivet. Send denne trinbesked til fejlsøgning; "
                     "send ikke adgangskoder eller nøgler.")
    result = st.session_state.get("season_backup_download")
    if result:
        name, content, count = result
        st.write(f"{name} — {len(content) / 1024 / 1024:.1f} MB, {count} dokumenter")
        st.download_button("Download backup (ZIP)", content, file_name=name,
                           mime="application/zip", on_click="ignore", key="download_season_backup")
        st.caption("Filen er ikke gemt på NAS’en endnu. ZIP-filen indeholder persondata og er ikke krypteret. "
                   "En vellykket filkontrol erstatter ikke en prøvegendannelse.")
        if st.button("Fjern download fra denne session", key="clear_season_backup"):
            st.session_state.pop("season_backup_download", None)
            st.rerun()
