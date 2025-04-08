import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from imblearn.over_sampling import SMOTE
import pickle  # Para salvar e carregar o modelo treinado
import matplotlib.pyplot as plt  # Para gerar gráficos

# Função para coletar os LOG's da planilha
def carregar_dados(usuario_arquivo, conta_arquivo, transferencia_arquivo, novo_usuario, nova_conta):
    usuarios = pd.read_csv(usuario_arquivo, encoding='latin1')
    contas = pd.read_csv(conta_arquivo, encoding='latin1')
    transferencias = pd.read_csv(transferencia_arquivo, encoding='latin1')
    novos_user = pd.read_csv(novo_usuario, encoding='latin1')
    novas_contas = pd.read_csv(nova_conta, encoding='latin1')

    return usuarios, contas, transferencias, novos_user, novas_contas

def preprocesamento_dados(transferencias):
    # Normaliza os valores de transferência.
    transferencias['valor_transferencia'] = transferencias['valor_transferencia'].astype(str)
    transferencias['valor_transferencia'] = transferencias['valor_transferencia'].str.replace(',', '.', regex=False)
    transferencias['valor_transferencia'] = pd.to_numeric(transferencias['valor_transferencia'], errors='coerce')

    return transferencias

# Função para treinar minha IA
def treinando_modelo(transferencias):
    X = transferencias[['valor_transferencia']]
    y = transferencias['validacao'].apply(lambda x: 1 if x == 'Fraude' else 0)

    if len(y.value_counts()) < 2:
        raise ValueError("O conjunto de dados não possui ambas as classes ('Fraude' e 'Não Fraude').")

    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X, y)

    X_treinando, X_test, y_treinando, y_test = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42)

    modelo = LogisticRegression()
    modelo.fit(X_treinando, y_treinando)

    # Previsão com limiar ajustado para aumentar sensibilidade a fraudes
    y_proba = modelo.predict_proba(X_test)[:, 1]  # Probabilidade de ser fraude
    limiar = 0.3  # Limiar reduzido para aumentar detecção de fraudes
    y_pred = (y_proba >= limiar).astype(int)

    acuracia = accuracy_score(y_test, y_pred)
    print(f"Acurácia do modelo: {acuracia:.2%}")

    print("\nRelatório de Classificação:")
    print(classification_report(y_test, y_pred, target_names=['Não Fraude', 'Fraude']))

    with open('modelo_fraude.pkl', 'wb') as f:
        pickle.dump(modelo, f)

    return modelo

# Função para prever as transferências
def prever_transferencias(novas_transferencias, novas_contas, novos_user):
    novas_transferencias['valor_transferencia'] = novas_transferencias['valor_transferencia'].astype(str)
    novas_transferencias['valor_transferencia'] = novas_transferencias['valor_transferencia'].str.replace('.', '', regex=False)
    novas_transferencias['valor_transferencia'] = novas_transferencias['valor_transferencia'].str.replace(',', '.', regex=False)
    novas_transferencias['valor_transferencia'] = pd.to_numeric(novas_transferencias['valor_transferencia'], errors='coerce')
    novas_transferencias = novas_transferencias[novas_transferencias['valor_transferencia'] > 0]

    # 🔧 Padroniza os IDs removendo espaços e convertendo para string
    novas_transferencias['id_fez_tranferencia'] = novas_transferencias['id_fez_tranferencia'].astype(str).str.strip()
    novas_contas['Id_usuario'] = novas_contas['Id_usuario'].astype(str).str.strip()

    # 🔍 Verifica se há correspondência real
    print("\n📌 IDs presentes nas transferências (análise):", list(novas_transferencias['id_fez_tranferencia'].unique()))
    print("📌 IDs presentes nas contas:", list(novas_contas['Id_usuario'].unique()))

    # Faz o merge
    novas_transferencias = novas_transferencias.merge(
        novas_contas[['Id_usuario', 'Saldo']], how='left',
        left_on='id_fez_tranferencia', right_on='Id_usuario'
    )

    # Converte saldo para float (tratando vírgulas e pontos)
    novas_transferencias['Saldo'] = novas_transferencias['Saldo'].astype(str)
    novas_transferencias['Saldo'] = novas_transferencias['Saldo'].str.replace('.', '', regex=False)
    novas_transferencias['Saldo'] = novas_transferencias['Saldo'].str.replace(',', '.', regex=False)
    novas_transferencias['Saldo'] = pd.to_numeric(novas_transferencias['Saldo'], errors='coerce')

    # Exibe para depuração
    print("\n🔍 Dados após merge com contas:")
    print(novas_transferencias[['id_fez_tranferencia', 'valor_transferencia', 'Saldo']])

    # Comparando se foi fraude ou não
    novas_transferencias['fraude_prevista'] = novas_transferencias.apply(
        lambda x: 'Fraude' if x['valor_transferencia'] > x['Saldo'] else 'Não Fraude', axis=1
    )

    return novas_transferencias

# Função principal do sistema irá executar todas as outras funções definidas no arquivo
def main():
    usuarios, contas, transferencias, novos_user, novas_contas = carregar_dados(
        'dados_treinamento/usuario_arquivo.csv',
        'dados_treinamento/conta_arquivo.csv',
        'dados_treinamento/transferencia_arquivo.csv',
        'dados_analise/novos_usuarios.csv',
        'dados_analise/novas_contas.csv'
    )

    transferencias = preprocesamento_dados(transferencias)
    modelo = treinando_modelo(transferencias)

    novas_transferencias = pd.read_csv('dados_analise/novas_transferencias.csv', encoding='latin1')
    novas_transferencias = prever_transferencias(novas_transferencias, novas_contas, novos_user)

    print("\nRelatório de previsão das tranferências!")
    print(novas_transferencias[['id_fez_tranferencia', 'valor_transferencia', 'fraude_prevista']])

    # 📊 Gerando gráfico de barras das previsões
    contagem = novas_transferencias['fraude_prevista'].value_counts()
    contagem = contagem.reindex(['Fraude', 'Não Fraude'], fill_value=0)  # garante as duas categorias

    contagem.plot(kind='bar', color=['red', 'green'])
    plt.title('Previsões de Fraude nas Transferências')
    plt.xlabel('Categoria')
    plt.ylabel('Quantidade')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()

# Garante que o bloco de código sejá processado se este arquivo for executado
if __name__ == "__main__":
    main()

# Operações reais onde este sistema pode ser utilizado: Aplicativos de Fintech: Alelo
