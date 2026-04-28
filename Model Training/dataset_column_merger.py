import pandas as pd
import random

def build_messy_resume(row):
    """Simulates truly unstructured, varied resume text without obvious headers."""
    
    # Template 1: Paragraph/Narrative style
    t1 = f"{row['career_objective']} Previously, I worked as a {row['positions']} at {row['professional_company_names']}. I hold a {row['degree_names']} in {row['major_field_of_studies']} from {row['educational_institution_name']}, graduating in {row['passing_years']}. My technical toolkit includes {row['skills']} and I have certifications in {row['certification_skills']}. I am fluent in {row['languages']}."
    
    # Template 2: Messy bullet-less list style
    t2 = f"Role: {row['positions']} @ {row['professional_company_names']}. {row['career_objective']} Graduated {row['passing_years']} from {row['educational_institution_name']} ({row['degree_names']} - {row['major_field_of_studies']}). Proficiencies: {row['skills']}. Extra certs: {row['certification_skills']}. Languages: {row['languages']}."
    
    # Template 3: Lead with Education and Skills
    t3 = f"Alumni of {row['educational_institution_name']} ({row['passing_years']}) with a {row['degree_names']} in {row['major_field_of_studies']}. Expert in {row['skills']}. Certified in {row['certification_skills']}. Professional background includes time at {row['professional_company_names']} as a {row['positions']}. {row['career_objective']} Languages spoken: {row['languages']}."

    # Randomly pick a format for each row to confuse the NER model
    return random.choice([t1, t2, t3])

def main():
    print("Loading the 9.5k row dataset...")
    df = pd.read_csv('fairlens_dataset_structured.csv')
    df = df.fillna("")

    print("Generating chaotic, unstructured text blocks...")
    df['Raw_Resume_Text'] = df.apply(build_messy_resume, axis=1)

    columns_to_keep = [
        'Raw_Resume_Text', 'gender', 'age_group', 'college_tier', 
        'region', 'protected_group', 'matched_score', 'shortlisted'
    ]
    df_pipeline_ready = df[columns_to_keep]

    output_file = 'fairlens_dataset_unstructured.csv'
    df_pipeline_ready.to_csv(output_file, index=False)
    print(f"Extraction complete. {len(df_pipeline_ready)} messy records saved to {output_file}")

if __name__ == "__main__":
    main()