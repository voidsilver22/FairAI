import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from dann_model import FairLensDANN 
import time

def discover_protected_columns(df, exclude=['Raw_Resume_Text', 'matched_score', 'protected_group']):
    discovered_cols = []
    for col in df.columns:
        if col not in exclude and df[col].nunique() < 10:
            if isinstance(df[col].dropna().iloc[0], str):
                discovered_cols.append(col)
    return discovered_cols

def auto_configure_bias(df, feature_col, score_col='matched_score', threshold=0.70):
    selection_rates = df.groupby(feature_col).apply(lambda x: (x[score_col] >= threshold).mean())
    unpriv_class = selection_rates.idxmin()
    priv_class = selection_rates.idxmax()
    
    sr_unpriv = selection_rates[unpriv_class]
    sr_priv = selection_rates[priv_class]
    di = sr_unpriv / sr_priv if sr_priv > 0 else 0
    weight = 1.0 + ((0.80 - di) * 5.0) if di < 0.80 else 1.0
    return unpriv_class, weight

def main():
    print("1. Scanning Dataset for Demographics...")
    df = pd.read_csv('fairlens_dataset_unstructured.csv')
    protected_columns = discover_protected_columns(df)
    
    dynamic_weights = {}
    target_columns = []
    
    for col in protected_columns:
        target_val, weight = auto_configure_bias(df, col)
        dynamic_weights[col] = weight
        target_col_name = f'target_{col}'
        df[target_col_name] = (df[col] == target_val).astype(float)
        target_columns.append(target_col_name)
    
    print("\n2. Vectorizing Resumes...")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    X_embeddings = embed_model.encode(df['Raw_Resume_Text'].tolist(), show_progress_bar=True)
    
    X = torch.tensor(X_embeddings, dtype=torch.float32)
    y_score = torch.tensor(df['matched_score'].values, dtype=torch.float32).view(-1, 1)
    y_adv = torch.tensor(df[target_columns].values, dtype=torch.float32)
    
    X_train, X_test, ys_tr, ys_te, yadv_tr, yadv_te = train_test_split(
        X, y_score, y_adv, test_size=0.2, random_state=42
    )
    
    train_dataset = TensorDataset(X_train, ys_tr, yadv_tr)
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    
    print("\n3. Initializing DANN (Capacity: 512 Neurons)...")
    model = FairLensDANN(protected_columns=protected_columns, input_dim=384, hidden_dim=512)
    
    criterion_score = nn.MSELoss() 
    criterion_adv = nn.BCELoss()   
    
    # Lower learning rate to stabilize the aggressive Smart Balancer
    optimizer = optim.Adam(model.parameters(), lr=0.0003)
    
    epochs = 30
    total_steps = epochs * len(train_loader)
    current_step = 0
    
    print("\n4. Starting Training...")
    start_time = time.time()
    
    for epoch in range(epochs):
        model.train()
        total_score_loss = 0
        total_samples = 0
        adv_correct = {col: 0 for col in protected_columns}
        
        for batch_x, b_score, b_adv in train_loader:
            optimizer.zero_grad()
            p = float(current_step) / total_steps
            alpha = 2. / (1. + np.exp(-10 * p)) - 1
            
            pred_score, adv_predictions_dict = model(batch_x, alpha=alpha)
            
            # --- THE MEGAPHONE FIX ---
            loss_score = criterion_score(pred_score, b_score)
            scaled_score_loss = loss_score * 50.0 
            total_loss = scaled_score_loss
            
            for idx, col in enumerate(protected_columns):
                pred_adv = adv_predictions_dict[col]
                true_adv = b_adv[:, idx].unsqueeze(1) 
                
                loss_adv = criterion_adv(pred_adv, true_adv)
                total_loss += (loss_adv * dynamic_weights[col])
                
                binary_preds = (pred_adv >= 0.5).float()
                adv_correct[col] += (binary_preds == true_adv).sum().item()
            
            total_loss.backward()
            optimizer.step()
            
            total_score_loss += loss_score.item()
            total_samples += b_adv.size(0)
            current_step += 1
            
        # --- SMART BALANCER (Capped at 1.5x) ---
        for col in protected_columns:
            adv_acc = adv_correct[col] / total_samples
            if adv_acc > 0.60:
                dynamic_weights[col] = min(dynamic_weights[col] * 1.1, 1.5)
            elif adv_acc < 0.55:
                dynamic_weights[col] = max(dynamic_weights[col] * 0.8, 0.5)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            avg_score_loss = total_score_loss / len(train_loader)
            print(f"\nEpoch [{epoch+1:02d}/{epochs}] | Score MSE (Raw): {avg_score_loss:.4f}")
            print("  [Smart Weight Adjustments]:")
            for col in protected_columns:
                acc = (adv_correct[col] / total_samples) * 100
                print(f"   -> {col.upper()}: Acc {acc:.1f}% | New Weight: {dynamic_weights[col]:.2f}")

    print(f"\nTraining Complete in {(time.time() - start_time):.2f} seconds.")
    torch.save(model.state_dict(), 'fairlens_clean_model.pth')

if __name__ == "__main__":
    main()