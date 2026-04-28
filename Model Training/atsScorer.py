import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import joblib
import os

def main():
    dataset_path = 'fairlens_dataset_unstructured.csv'
    
    print("1. Loading unstructured dataset...")
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found. Please run the merger script first.")
        return
        
    df = pd.read_csv(dataset_path)

    print("2. Initializing NLP Embedding Model (all-MiniLM-L6-v2)...")
    # This converts the messy text into mathematical vectors
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')

    print("3. Vectorizing 9,500+ resumes (This will take a few minutes)...")
    # show_progress_bar gives you a nice loading bar in the terminal
    X = embed_model.encode(df['Raw_Resume_Text'].tolist(), show_progress_bar=True)
    y = df['matched_score']

    print("4. Splitting Data for Training/Testing (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("5. Training the Baseline ATS Model (Random Forest)...")
    # Using n_jobs=-1 uses all your CPU cores to train faster
    ats_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    ats_model.fit(X_train, y_train)

    print("6. Evaluating Model Accuracy...")
    test_predictions = ats_model.predict(X_test)
    mae = mean_absolute_error(y_test, test_predictions)
    print(f"   -> Mean Absolute Error: {mae:.4f} (Model is off by an average of {mae*100:.1f}%)")

    print("7. Generating Scores for the Entire Dataset...")
    # Now we predict scores for EVERYONE so your teammate can audit the results
    all_predictions = ats_model.predict(X)
    
    # Add the AI's predicted scores back into the dataframe
    df['Model_Predicted_Score'] = all_predictions

    print("8. Saving the Biased Baseline Model and Results...")
    # Save the model file
    joblib.dump(ats_model, 'biased_baseline_ats.pkl')
    
    # Save the results for the Audit Phase
    results_df = df[['Raw_Resume_Text', 'gender', 'age_group', 'college_tier', 'region', 'protected_group', 'matched_score', 'Model_Predicted_Score']]
    results_df.to_csv('baseline_scored_results.csv', index=False)
    
    print("\n✅ SUCCESS!")
    print("- Model saved to: 'biased_baseline_ats.pkl'")
    print("- Predictions saved to: 'baseline_scored_results.csv'")
    print("\nNext Step: Hand 'baseline_scored_results.csv' to your teammate. They can plug this directly into Fairlearn/AIF360 to prove the model is biased!")

if __name__ == "__main__":
    main()