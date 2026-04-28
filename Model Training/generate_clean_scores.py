import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from dann_model import FairLensDANN

def discover_protected_columns(df, exclude=['Raw_Resume_Text', 'matched_score', 'protected_group']):
    discovered_cols = []
    for col in df.columns:
        if col not in exclude and df[col].nunique() < 10:
            if isinstance(df[col].dropna().iloc[0], str):
                discovered_cols.append(col)
    return discovered_cols

def main():
    print("1. Loading dataset and embedding model...")
    df = pd.read_csv('fairlens_dataset_unstructured.csv')
    
    protected_columns = discover_protected_columns(df)
    print(f"  -> Model requires heads for: {protected_columns}")
    
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("\n2. Vectorizing resumes...")
    X_embeddings = embed_model.encode(df['Raw_Resume_Text'].tolist(), show_progress_bar=True)
    X_tensor = torch.tensor(X_embeddings, dtype=torch.float32)
    
    print("\n3. Loading the Debiased Dynamic FairLens Model...")
    # MUST MATCH TRAINING CAPACITY (hidden_dim=512)
    model = FairLensDANN(protected_columns=protected_columns, input_dim=384, hidden_dim=512)
    model.load_state_dict(torch.load('fairlens_clean_model.pth', weights_only=True))
    model.eval() 
    
    print("\n4. Generating Fair Scores...")
    with torch.no_grad():
        clean_scores, adv_dict = model(X_tensor, alpha=0.0) 
    
    df['FairLens_Predicted_Score'] = clean_scores.numpy().flatten()
    
    output_cols = ['Raw_Resume_Text'] + protected_columns + ['protected_group', 'matched_score', 'FairLens_Predicted_Score']
    output_df = df[output_cols]
    output_file = 'clean_scored_results.csv'
    output_df.to_csv(output_file, index=False)
    
    print(f"\n✅ SUCCESS! Dynamic clean scores saved to {output_file}")

if __name__ == "__main__":
    main()