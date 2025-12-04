import logging
import os
import getpass
import ssl
from ldap3 import Server, Connection, ALL, Tls

from app.config import get_settings


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    settings = get_settings()
    bind_dn = settings.ldap_bind_dn or os.getenv("LDAP_TEST_BIND_DN")
    bind_pw = settings.ldap_bind_password or os.getenv("LDAP_TEST_BIND_PASSWORD")
    if not bind_dn or not bind_pw:
        print(
            "Erreur: LDAP_BIND_DN / LDAP_BIND_PASSWORD manquants (ou LDAP_TEST_BIND_*)"
        )
        return

    given = os.getenv("LDAP_TEST_GIVENNAME") or input("givenName: ").strip()
    sn = os.getenv("LDAP_TEST_SN") or input("sn (nom de famille): ").strip()
    search_filter = f"(&(objectClass=user)(givenName={given}*)(sn={sn}*))"

    print(
        f"Debugging LDAP search with service account:\n"
        f"  server: {settings.ldap_server}\n"
        f"  bind_dn: {bind_dn}\n"
        f"  search_base: {settings.ldap_search_base}\n"
        f"  search_filter: {search_filter}\n"
    )

    # Force TLS 1.2 and a common cipher to match the AD endpoint expectations
    tls_config = Tls(
        validate=ssl.CERT_NONE,
        version=ssl.PROTOCOL_TLSv1_2,
        ciphers="ECDHE-RSA-AES256-GCM-SHA384",
    )
    use_ssl = settings.ldap_server.startswith("ldaps://")
    server = Server(settings.ldap_server, get_info=ALL, use_ssl=use_ssl, tls=tls_config)
    try:
        with Connection(server, user=bind_dn, password=bind_pw, auto_bind=True) as conn:
            ok = conn.search(
                search_base=settings.ldap_search_base,
                search_filter=search_filter,
                attributes=[
                    "sAMAccountName",
                    "cn",
                    "uid",
                    "mail",
                    "givenName",
                    "sn",
                    "distinguishedName",
                ],
            )
            print(
                f"Search ok? {ok}, entries: {len(conn.entries) if conn.entries else 0}"
            )
            if conn.entries:
                entry = conn.entries[0]
                print("First entry DN:", entry.entry_dn)
                for attr in [
                    "sAMAccountName",
                    "cn",
                    "uid",
                    "mail",
                    "givenName",
                    "sn",
                    "distinguishedName",
                ]:
                    val = entry.entry_attributes_as_dict.get(attr)
                    print(f"  {attr}: {val}")
    except Exception as exc:
        print(f"LDAP search failed: {exc}")


if __name__ == "__main__":
    main()
