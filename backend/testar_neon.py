
import getpass

import psycopg2


def main():
    print("TESTE DE CONEXÃO — NEON POSTGRESQL\n")

    host = input("Host do Neon: ").strip()
    database = input("Database [hes_atacado]: ").strip() or "hes_atacado"
    user = input("User [hes_atacado_owner]: ").strip() or "hes_atacado_owner"
    password = getpass.getpass("Password: ")

    try:
        with psycopg2.connect(
            host=host,
            dbname=database,
            user=user,
            password=password,
            port=5432,
            sslmode="require",
            connect_timeout=10,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user")
                banco, usuario = cursor.fetchone()

        print("\nCONEXÃO COM O NEON REALIZADA COM SUCESSO!")
        print(f"Banco: {banco}")
        print(f"Usuário: {usuario}")

    except psycopg2.Error as error:
        print("\nFALHA NA CONEXÃO.")
        print(f"Tipo: {type(error).__name__}")
        print("Confira as credenciais e a disponibilidade do Neon.")


if __name__ == "__main__":
    main()
