"""
Ponto de entrada do Bot de Alerta de Passagens.
Mantido para total retrocompatibilidade com Procfile, iniciar.sh e comandos existentes.
Toda a arquitetura do projeto foi modularizada e está organizada no pacote `src/`.
"""
from main import main

if __name__ == "__main__":
    main()
