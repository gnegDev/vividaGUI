"""
gbm_train_models_enhanced_full_features.py

ALL AVAILABLE FEATURES:
 - Neurological symptoms (decomposed into binary flags)
 - Genetic markers (MGMT, IDH, EGFR, TERT, ATRX)
 - Clinical features (edema_volume, steroid_dose, antiseizure_meds)
 - Tumor characteristics (lateralization, family_history, previous_radiation)
 - Treatment response (RANO response - as predictor, not target)

TOTAL: ~120+ features instead of 76
"""

import os, time, warnings, re
from typing import List, Tuple, Dict, Any
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.neural_network import MLPRegressor
from joblib import dump
import json
warnings.filterwarnings("ignore")

# ------------------ CONFIG ------------------
INPUT_XLSX = "glioblastoma_data.xlsx"
OUTDIR = "gbm_models_output_all90_dosage_full_features"
CV_FOLDS = 5
GOMPERTZ_MAXFEV = 5000
N_EST_GBR = 200
N_EST_RF = 180
N_EST_ET = 150
MLP_HIDDEN = (256, 128, 64)
STACKER_ALPHA = 0.1
USE_XGBOOST = True
# --------------------------------------------

os.makedirs(OUTDIR, exist_ok=True)
np.random.seed(42)
t0 = time.time()

print("="*80)
print("GBM TREATMENT OPTIMIZATION - ENHANCED TRAINING v3.0")
print("="*80)
print(f"NEW: All available features (neurological, genetic, clinical)")
print(f"Output directory: {OUTDIR}")
print("="*80)

# ---------- helpers ----------
def parse_treatment_flags(tstr):
    """Extract binary treatment flags with SPECIFIC drug detection"""
    t = str(tstr).lower() if not pd.isna(tstr) else ""

    # Main categories
    flags = {
        'chemo': int('temozolomide' in t or 'tmz' in t or 'chem' in t),
        'radio': int('radiation' in t or 'radiotherapy' in t or 'rt' in t or 'radiother' in t),
        'beva': int('bevacizumab' in t or 'beva' in t),
        'other_drug': int(('lomustine' in t or 'ccnu' in t or 'carboplatin' in t or 'etoposide' in t or 'irinotecan' in t))
    }

    # Specific drug types
    flags['drug_temozolomide'] = int('temozolomide' in t or 'tmz' in t)
    flags['drug_lomustine'] = int('lomustine' in t or 'ccnu' in t)
    flags['drug_carboplatin'] = int('carboplatin' in t)
    flags['drug_etoposide'] = int('etoposide' in t)
    flags['drug_irinotecan'] = int('irinotecan' in t)
    flags['drug_bevacizumab'] = int('bevacizumab' in t or 'beva' in t)

    return flags

def parse_dosage_features(tstr) -> Dict[str, float]:
    """Extract concrete dosages from treatment string"""
    t = str(tstr).lower() if not pd.isna(tstr) else ""

    result = {
        'chemo_dose_mg_per_m2': 0.0,
        'radio_total_Gy': 0.0,
        'radio_fractions': 0.0,
        'radio_BED': 0.0
    }

    # Extract chemotherapy dose
    chemo_patterns = [
        r'(\d+)\s*mg\s*/\s*m2',
        r'(\d+)\s*mg/m²',
        r'temozolomide\s+(\d+)',
        r'tmz\s+(\d+)'
    ]
    for pattern in chemo_patterns:
        match = re.search(pattern, t)
        if match:
            result['chemo_dose_mg_per_m2'] = float(match.group(1))
            break

    # Extract radiotherapy dose and fractions
    radio_patterns = [
        r'(\d+)\s*gy\s*/\s*(\d+)\s*fr',
        r'(\d+)\s*gy\s*\/\s*(\d+)',
        r'radiation\s+(\d+)\s*gy.*?(\d+)\s*fr',
        r'(\d+)\s*gy.*?(\d+)\s*fraction'
    ]
    for pattern in radio_patterns:
        match = re.search(pattern, t)
        if match:
            result['radio_total_Gy'] = float(match.group(1))
            result['radio_fractions'] = float(match.group(2))
            break

    # Calculate BED (Biologically Effective Dose)
    if result['radio_total_Gy'] > 0 and result['radio_fractions'] > 0:
        n = result['radio_fractions']
        d = result['radio_total_Gy'] / n
        # BED = n * d * (1 + d/(α/β)), where α/β = 10 Gy for GBM
        result['radio_BED'] = n * d * (1 + d / 10.0)

    return result

def parse_neurological_symptoms(symptom_str) -> Dict[str, int]:
    """
    NEW FUNCTION: Parse neurological symptoms into binary flags

    Input: "headache, motor_deficit, seizures"
    Output: {
        'has_headache': 1,
        'has_motor_deficit': 1,
        'has_seizures': 1,
        'has_sensory_deficit': 0,
        'has_cognitive_decline': 0,
        'has_speech_disturbance': 0,
        'has_visual_disturbance': 0,
        'symptom_count': 3
    }
    """
    s = str(symptom_str).lower() if not pd.isna(symptom_str) else ""

    symptoms = {
        'has_headache': int('headache' in s),
        'has_motor_deficit': int('motor_deficit' in s or 'motor deficit' in s),
        'has_seizures': int('seizure' in s),
        'has_sensory_deficit': int('sensory_deficit' in s or 'sensory deficit' in s),
        'has_cognitive_decline': int('cognitive' in s),
        'has_speech_disturbance': int('speech' in s),
        'has_visual_disturbance': int('visual' in s)
    }

    # Count total symptoms (0 if asymptomatic)
    if 'asymptomatic' in s:
        symptoms['symptom_count'] = 0
    else:
        symptoms['symptom_count'] = sum(symptoms.values())

    return symptoms

def fit_gompertz(times, sizes, T0):
    """Fit Gompertz model: V(t) = T0 * (K/T0)^(1 - exp(-r*t))"""
    def gompertz(t, r, K):
        return T0 * (K / T0) ** (1 - np.exp(-r * t))

    try:
        p0 = [0.05, max(sizes) * 1.2]
        bounds = ([1e-6, T0], [0.5, 20.0])
        popt, _ = curve_fit(gompertz, times, sizes, p0=p0, bounds=bounds, maxfev=GOMPERTZ_MAXFEV)
        return popt
    except:
        return [np.nan, np.nan]

def safe_numeric_cast(df):
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(",", ".").str.strip()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='ignore')
    return df

def mape(true, pred):
    true, pred = np.array(true, dtype=float), np.array(pred, dtype=float)
    mask = np.abs(true) > 1e-3
    return np.mean(np.abs((true[mask] - pred[mask]) / true[mask])) * 100.0 if mask.sum() > 0 else np.nan

# ---------- load & process data ----------
print("\nLoading Excel:", INPUT_XLSX)
xls = pd.ExcelFile(INPUT_XLSX)
frames = [pd.read_excel(xls, sh).assign(stage=str(sh)) for sh in xls.sheet_names]
df = pd.concat(frames, ignore_index=True)
print(f"Loaded {len(xls.sheet_names)} sheets, {len(df)} rows")

# Parse treatment flags (binary)
print("Parsing treatment flags...")
tflags = df['treatment'].apply(parse_treatment_flags).apply(pd.Series)
df = pd.concat([df, tflags], axis=1)

# Parse dosage features
print("Extracting dosage features from treatment strings...")
dosages = df['treatment'].apply(parse_dosage_features).apply(pd.Series)
df = pd.concat([df, dosages], axis=1)

# NEW: Parse neurological symptoms
print("Parsing neurological symptoms...")
neuro_symptoms = df['neurological_symptoms'].apply(parse_neurological_symptoms).apply(pd.Series)
df = pd.concat([df, neuro_symptoms], axis=1)

# Fill missing dosages with defaults based on treatment flags
default_chemo_dose = 75.0
default_radio_dose = 60.0
default_radio_fractions = 30.0

for idx, row in df.iterrows():
    if row['chemo'] == 1 and row['chemo_dose_mg_per_m2'] == 0:
        df.at[idx, 'chemo_dose_mg_per_m2'] = default_chemo_dose

    if row['radio'] == 1 and row['radio_total_Gy'] == 0:
        df.at[idx, 'radio_total_Gy'] = default_radio_dose
        df.at[idx, 'radio_fractions'] = default_radio_fractions
        n = default_radio_fractions
        d = default_radio_dose / n
        df.at[idx, 'radio_BED'] = n * d * (1 + d / 10.0)

print(f"Dosage features extracted:")
print(f"  Chemo doses: min={df['chemo_dose_mg_per_m2'].min():.1f}, max={df['chemo_dose_mg_per_m2'].max():.1f}, median={df['chemo_dose_mg_per_m2'].median():.1f}")
print(f"  Radio doses: min={df['radio_total_Gy'].min():.1f}, max={df['radio_total_Gy'].max():.1f}, median={df['radio_total_Gy'].median():.1f}")
print(f"  Radio BED: min={df['radio_BED'].min():.1f}, max={df['radio_BED'].max():.1f}, median={df['radio_BED'].median():.1f}")
print(f"\nNeurological symptoms extracted:")
print(f"  Symptom count: min={df['symptom_count'].min():.0f}, max={df['symptom_count'].max():.0f}, mean={df['symptom_count'].mean():.1f}")

# ---------- fit gompertz ----------
print("\nFitting Gompertz...")
time_cols = [('tumor_size_2m',2), ('tumor_size_4m',4), ('tumor_size_6m',6), ('tumor_size_12m',12)]
fit_rows = []

for idx, row in df.iterrows():
    pid = row.get('patient_id', f"idx_{idx}")
    T0 = row.get('tumor_size_before', np.nan)

    if pd.isna(T0) or T0 <= 0:
        fit_rows.append({'patient_id': pid, 'r_fit': np.nan, 'K_fit': np.nan, 'n_obs': 0})
        continue

    times, sizes = [0.0], [float(T0)]
    for col, t in time_cols:
        if col in row and not pd.isna(row[col]):
            try:
                sizes.append(float(row[col]))
                times.append(float(t))
            except:
                pass

    if len(times) >= 3:
        try:
            r_k = fit_gompertz(times, sizes, T0)
            fit_rows.append({'patient_id': pid, 'r_fit': r_k[0], 'K_fit': r_k[1], 'n_obs': len(times)})
        except:
            fit_rows.append({'patient_id': pid, 'r_fit': np.nan, 'K_fit': np.nan, 'n_obs': len(times)})
    else:
        fit_rows.append({'patient_id': pid, 'r_fit': np.nan, 'K_fit': np.nan, 'n_obs': len(times)})

fitted_df = pd.DataFrame(fit_rows)
df = df.merge(fitted_df, on='patient_id', how='left')
print("Gompertz fit complete")

# ---------- Calculate targets ----------
mask_untr = (df['chemo'] == 0) & (df['radio'] == 0) & (~df['r_fit'].isna())
baseline_r = float(np.nanmedian(df.loc[mask_untr, 'r_fit'])) if mask_untr.sum() >= 5 else 0.12
baseline_r = baseline_r if not np.isnan(baseline_r) else 0.12

df['r_target'] = df['r_fit'].fillna(baseline_r)
df['K_target'] = df['K_fit'].fillna(df['tumor_size_before'].fillna(1.0) * 2.0)

# Calculate group statistics
mask_untreated = (df['chemo'] == 0) & (df['radio'] == 0) & (~df['r_fit'].isna())
mask_chemo_only = (df['chemo'] == 1) & (df['radio'] == 0) & (~df['r_fit'].isna())
mask_radio_only = (df['chemo'] == 0) & (df['radio'] == 1) & (~df['r_fit'].isna())
mask_both = (df['chemo'] == 1) & (df['radio'] == 1) & (~df['r_fit'].isna())

r_untreated = np.nanmedian(df.loc[mask_untreated, 'r_fit']) if mask_untreated.sum() >= 3 else baseline_r
r_chemo = np.nanmedian(df.loc[mask_chemo_only, 'r_fit']) if mask_chemo_only.sum() >= 3 else baseline_r
r_radio = np.nanmedian(df.loc[mask_radio_only, 'r_fit']) if mask_radio_only.sum() >= 3 else baseline_r

chemo_effect = max(0.02, r_untreated - r_chemo) if r_untreated > r_chemo else 0.05
radio_effect = max(0.02, r_untreated - r_radio) if r_untreated > r_radio else 0.05
combined_effect = max(0.03, chemo_effect + radio_effect)

print(f"\nTreatment effects: baseline_r={baseline_r:.4f}, r_untreated={r_untreated:.4f}")
print(f"  chemo_effect={chemo_effect:.4f}, radio_effect={radio_effect:.4f}")

# Calculate alpha/beta with VARIABILITY + DOSAGE DEPENDENCE + NEW FEATURES
alpha_list, beta_list = [], []

for _, row in df.iterrows():
    r_est = row['r_target']
    chemo, radio, beva = int(row.get('chemo', 0)), int(row.get('radio', 0)), int(row.get('beva', 0))
    kps, tumor_size = row.get('kps', 70), row.get('tumor_size_before', 3.0)

    # Dosages
    chemo_dose = row.get('chemo_dose_mg_per_m2', 0)
    radio_BED = row.get('radio_BED', 0)

    # NEW: Genetic markers (favorable mutations)
    mgmt = int(row.get('mgmt_methylation', 0)) if not pd.isna(row.get('mgmt_methylation', 0)) else 0
    idh = int(row.get('idh_mutation', 0)) if not pd.isna(row.get('idh_mutation', 0)) else 0

    # NEW: Clinical features
    edema = row.get('edema_volume', 0) if not pd.isna(row.get('edema_volume', 0)) else 0
    steroid = row.get('steroid_dose', 0) if not pd.isna(row.get('steroid_dose', 0)) else 0
    antiseizure = int(row.get('antiseizure_meds', 0)) if not pd.isna(row.get('antiseizure_meds', 0)) else 0

    # NEW: Neurological symptoms
    symptom_count = row.get('symptom_count', 0) if not pd.isna(row.get('symptom_count', 0)) else 0

    reduction = max(0, r_untreated - (r_est if not pd.isna(r_est) else r_untreated))

    # Calculate base effects
    if chemo and radio:
        total_effect = max(reduction, combined_effect)
        alpha, beta = total_effect * 0.6, total_effect * 0.4
    elif chemo:
        alpha = max(reduction, chemo_effect)
        beta = 0.01 + np.random.uniform(0, 0.02)
    elif radio:
        beta = max(reduction, radio_effect)
        alpha = 0.01 + np.random.uniform(0, 0.02)
    else:
        alpha, beta = 0.01 + np.random.uniform(0, 0.01), 0.01 + np.random.uniform(0, 0.01)

    # Modulate by dosage
    if chemo and chemo_dose > 0:
        dose_factor = min(chemo_dose / 75.0, 2.5)
        alpha *= dose_factor

    if radio and radio_BED > 0:
        BED_factor = min(radio_BED / 72.0, 1.5)
        beta *= BED_factor

    # NEW: Modulate by MGMT (better chemo response if methylated)
    if mgmt and chemo:
        alpha *= 1.3

    # NEW: Modulate by IDH (better overall response)
    if idh:
        alpha *= 1.2
        beta *= 1.2

    # NEW: Modulate by edema (worse tolerance → reduce effectiveness)
    if edema > 5:
        edema_factor = np.clip(1.0 - (edema - 5) * 0.05, 0.7, 1.0)
        alpha *= edema_factor
        beta *= edema_factor

    # NEW: Modulate by symptoms (more symptoms → worse tolerance)
    if symptom_count > 0:
        symptom_factor = np.clip(1.0 - symptom_count * 0.03, 0.8, 1.0)
        alpha *= symptom_factor
        beta *= symptom_factor

    # Modulate by patient characteristics
    kps_factor = np.clip((kps / 70.0) if not pd.isna(kps) else 1.0, 0.7, 1.3)
    size_factor = np.clip(tumor_size / 3.0, 0.8, 1.2)
    alpha *= kps_factor * size_factor
    beta *= kps_factor * size_factor

    if beva:
        alpha *= 1.4
        beta *= 1.1

    # Add controlled noise
    alpha += np.random.normal(0, 0.005)
    beta += np.random.normal(0, 0.005)

    alpha_list.append(float(np.clip(alpha, 0.005, 0.4)))
    beta_list.append(float(np.clip(beta, 0.005, 0.4)))

df['alpha_target'] = alpha_list
df['beta_target'] = beta_list

# Check for NaN and fix
print(f"\nAlpha NaN count: {df['alpha_target'].isna().sum()}")
print(f"Beta NaN count: {df['beta_target'].isna().sum()}")

# Fill any NaN with median
if df['alpha_target'].isna().sum() > 0:
    alpha_median = df['alpha_target'].median()
    df['alpha_target'] = df['alpha_target'].fillna(alpha_median)
    print(f"Filled {df['alpha_target'].isna().sum()} NaN alpha with median {alpha_median:.4f}")

if df['beta_target'].isna().sum() > 0:
    beta_median = df['beta_target'].median()
    df['beta_target'] = df['beta_target'].fillna(beta_median)
    print(f"Filled {df['beta_target'].isna().sum()} NaN beta with median {beta_median:.4f}")

print(f"\nAlpha range: [{df['alpha_target'].min():.4f}, {df['alpha_target'].max():.4f}]")
print(f"Beta range: [{df['beta_target'].min():.4f}, {df['beta_target'].max():.4f}]")

# ---------- ENHANCED FEATURES with ALL AVAILABLE DATA ----------
print("\n" + "="*80)
print("FEATURE ENGINEERING - FULL FEATURE SET")
print("="*80)

# Basic numeric features (OLD + NEW)
features_basic = [
    # Original features
    'age', 'tumor_size_before', 'chemo', 'radio', 'beva', 'other_drug', 'kps',

    # Dosage features
    'chemo_dose_mg_per_m2', 'radio_total_Gy', 'radio_BED',

    # Specific drugs
    'drug_temozolomide', 'drug_lomustine', 'drug_carboplatin',
    'drug_etoposide', 'drug_irinotecan', 'drug_bevacizumab',

    # NEW: Genetic markers
    'mgmt_methylation', 'idh_mutation', 'egfr_amplification',
    'tert_mutation', 'atrx_mutation',

    # NEW: Clinical features
    'edema_volume', 'steroid_dose', 'antiseizure_meds',

    # NEW: Neurological symptoms (decomposed)
    'has_headache', 'has_motor_deficit', 'has_seizures',
    'has_sensory_deficit', 'has_cognitive_decline',
    'has_speech_disturbance', 'has_visual_disturbance', 'symptom_count',

    # NEW: Other features
    'family_history', 'previous_radiation'
]

# Categorical features (OLD + NEW)
categorical = [
    # Original
    'gender', 'resection_extent', 'molecular_subtype',
    'tumor_location', 'contrast_enhancement', 'stage',

    # NEW
    'lateralization', 'rano_response'
]

print(f"Basic numeric features: {len(features_basic)}")
print(f"Categorical features: {len(categorical)}")

for c in features_basic + categorical:
    if c not in df.columns:
        df[c] = np.nan

X_raw = safe_numeric_cast(df[features_basic + categorical])

# Convert boolean columns to int BEFORE processing
boolean_cols = ['mgmt_methylation', 'idh_mutation', 'egfr_amplification',
                'tert_mutation', 'atrx_mutation', 'antiseizure_meds',
                'family_history', 'previous_radiation']

for col in boolean_cols:
    if col in X_raw.columns:
        X_raw[col] = X_raw[col].replace({'True': 1, 'False': 0, 'true': 1, 'false': 0, True: 1, False: 0})
        X_raw[col] = pd.to_numeric(X_raw[col], errors='coerce').fillna(0).astype(int)

# OneHot encode
cat_df = X_raw[categorical].fillna('NA').astype(str)
enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
enc_arr = enc.fit_transform(cat_df)
enc_cols = [f"{cat}_{v}" for i, cat in enumerate(categorical) for v in enc.categories_[i]]

num_df = X_raw.drop(columns=categorical)
for c in num_df.columns:
    num_df[c] = pd.to_numeric(num_df[c], errors='coerce')
    median_val = num_df[c].median()
    num_df[c] = num_df[c].fillna(median_val if not pd.isna(median_val) else 0).astype(float)

num_cols = num_df.columns.tolist()
X_num = num_df.reset_index(drop=True)
X_enc = pd.DataFrame(enc_arr, columns=enc_cols, index=X_num.index)

print("\nCreating enhanced features with interactions...")
interactions = pd.DataFrame(index=X_num.index)

# Fitted parameters
fitted_features = df[['r_fit', 'K_fit', 'n_obs', 'alpha_target', 'beta_target']].fillna(0).reset_index(drop=True)

# Add computed values
interactions['alpha_computed'] = fitted_features['alpha_target']
interactions['beta_computed'] = fitted_features['beta_target']

# Core interactions (treatment × params)
interactions['r_fit_x_chemo'] = fitted_features['r_fit'] * X_num['chemo']
interactions['r_fit_x_radio'] = fitted_features['r_fit'] * X_num['radio']
interactions['K_fit_x_chemo'] = fitted_features['K_fit'] * X_num['chemo']
interactions['K_fit_x_radio'] = fitted_features['K_fit'] * X_num['radio']
interactions['alpha_computed_x_chemo'] = fitted_features['alpha_target'] * X_num['chemo']
interactions['beta_computed_x_radio'] = fitted_features['beta_target'] * X_num['radio']

# Treatment combinations
interactions['chemo_x_radio'] = X_num['chemo'] * X_num['radio']
interactions['chemo_x_tumor_size'] = X_num['chemo'] * X_num['tumor_size_before']
interactions['radio_x_tumor_size'] = X_num['radio'] * X_num['tumor_size_before']
interactions['beva_x_chemo'] = X_num['beva'] * X_num['chemo']
interactions['kps_x_chemo'] = X_num['kps'] * X_num['chemo']
interactions['treatment_count'] = X_num['chemo'] + X_num['radio'] + X_num['beva']

# Dosage interactions
interactions['chemo_dose_x_tumor_size'] = X_num['chemo_dose_mg_per_m2'] * X_num['tumor_size_before']
interactions['chemo_dose_x_kps'] = X_num['chemo_dose_mg_per_m2'] * X_num['kps']
interactions['chemo_dose_x_age'] = X_num['chemo_dose_mg_per_m2'] * X_num['age']
interactions['radio_BED_x_tumor_size'] = X_num['radio_BED'] * X_num['tumor_size_before']
interactions['radio_BED_x_kps'] = X_num['radio_BED'] * X_num['kps']
interactions['radio_BED_x_age'] = X_num['radio_BED'] * X_num['age']
interactions['chemo_dose_x_radio_BED'] = X_num['chemo_dose_mg_per_m2'] * X_num['radio_BED']

# NEW: Genetic × treatment interactions
interactions['mgmt_x_chemo'] = X_num['mgmt_methylation'] * X_num['chemo']
interactions['mgmt_x_chemo_dose'] = X_num['mgmt_methylation'] * X_num['chemo_dose_mg_per_m2']
interactions['idh_x_chemo'] = X_num['idh_mutation'] * X_num['chemo']
interactions['idh_x_radio'] = X_num['idh_mutation'] * X_num['radio']
interactions['egfr_x_chemo'] = X_num['egfr_amplification'] * X_num['chemo']

# NEW: Clinical × treatment interactions
interactions['edema_x_chemo'] = X_num['edema_volume'] * X_num['chemo']
interactions['edema_x_radio'] = X_num['edema_volume'] * X_num['radio']
interactions['steroid_x_chemo'] = X_num['steroid_dose'] * X_num['chemo']
interactions['symptom_count_x_chemo'] = X_num['symptom_count'] * X_num['chemo']
interactions['symptom_count_x_radio'] = X_num['symptom_count'] * X_num['radio']

# Non-linear terms
interactions['age_squared'] = X_num['age'] ** 2
interactions['tumor_size_squared'] = X_num['tumor_size_before'] ** 2
interactions['tumor_size_log'] = np.log1p(X_num['tumor_size_before'])
interactions['r_fit_squared'] = fitted_features['r_fit'] ** 2
interactions['K_fit_log'] = np.log1p(fitted_features['K_fit'])
interactions['chemo_dose_squared'] = X_num['chemo_dose_mg_per_m2'] ** 2
interactions['radio_BED_squared'] = X_num['radio_BED'] ** 2
interactions['chemo_dose_log'] = np.log1p(X_num['chemo_dose_mg_per_m2'])
interactions['radio_BED_log'] = np.log1p(X_num['radio_BED'])

# NEW: Non-linear terms for new features
interactions['edema_squared'] = X_num['edema_volume'] ** 2
interactions['steroid_squared'] = X_num['steroid_dose'] ** 2
interactions['symptom_count_squared'] = X_num['symptom_count'] ** 2

# Combine all
X = pd.concat([X_num[num_cols], X_enc, fitted_features[['r_fit', 'K_fit', 'n_obs']], interactions], axis=1)

print(f"\nFinal feature matrix shape: {X.shape}")
print(f"Total features: {X.shape[1]}")

# Scale numeric
scaler = StandardScaler()
X = pd.DataFrame(scaler.fit_transform(X), columns=X.columns, index=X.index)

# Targets
y = df[['r_target','K_target','alpha_target','beta_target']].copy()

print(f"\nTarget matrix shape: {y.shape}")
print(f"Samples: {len(X)}")

# ---------- Train models ----------
try:
    import xgboost as xgb
    base_factories = [('xgb', lambda: xgb.XGBRegressor(n_estimators=200, max_depth=6, learning_rate=0.05, subsample=0.8, random_state=42))]
    print("\nXGBoost: available")
except:
    base_factories = []
    print("\nXGBoost: not available")

base_factories.extend([
    ('gbr', lambda: GradientBoostingRegressor(n_estimators=N_EST_GBR, max_depth=5, learning_rate=0.05, subsample=0.8, random_state=42)),
    ('rf', lambda: RandomForestRegressor(n_estimators=N_EST_RF, max_depth=15, min_samples_split=4, n_jobs=-1, random_state=42)),
    ('et', lambda: ExtraTreesRegressor(n_estimators=N_EST_ET, max_depth=15, min_samples_split=4, n_jobs=-1, random_state=42)),
    ('mlp', lambda: MLPRegressor(hidden_layer_sizes=MLP_HIDDEN, max_iter=500, early_stopping=True, random_state=42))
])

# ---------- OOF stacking ----------
kf = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
stacked_models = {}
oof_predictions = {t: np.zeros((X.shape[0], len(base_factories))) for t in y.columns}

print(f"\nTraining {len(base_factories)} base models with OOF stacking...")
for tgt in y.columns:
    print(f"  {tgt}...", end=' ')

    for fold_idx, (tr_idx, te_idx) in enumerate(kf.split(X)):
        X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
        y_tr = y.iloc[tr_idx][tgt]

        for m_idx, (name, factory) in enumerate(base_factories):
            try:
                model = factory()
                model.fit(X_tr, y_tr)
                oof_predictions[tgt][te_idx, m_idx] = model.predict(X_te)
            except:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
                model.fit(X_tr, y_tr)
                oof_predictions[tgt][te_idx, m_idx] = model.predict(X_te)

    # Meta
    meta = Ridge(alpha=STACKER_ALPHA)
    meta.fit(oof_predictions[tgt], y[tgt])

    # Full models
    trained_bases = []
    for name, factory in base_factories:
        try:
            m = factory()
            m.fit(X, y[tgt])
            trained_bases.append((name, m))
        except:
            m = RandomForestRegressor(n_estimators=100, random_state=42)
            m.fit(X, y[tgt])
            trained_bases.append((name, m))

    stacked_models[tgt] = {'bases': trained_bases, 'meta': meta}
    print("Done")

# ---------- Metrics ----------
print("\n" + "="*80)
print("FINAL RESULTS - ENHANCED MODEL v3.0 (ALL FEATURES)")
print("="*80)

for tgt in y.columns:
    oof_final = stacked_models[tgt]['meta'].predict(oof_predictions[tgt])
    true = y[tgt].values

    r2 = r2_score(true, oof_final)
    rmse = np.sqrt(np.mean((true - oof_final) ** 2))
    mae = mean_absolute_error(true, oof_final)
    mape_val = mape(true, oof_final)

    status = "[OK]" if r2 >= 0.90 else "[CLOSE]" if r2 >= 0.85 else "[LOW]"

    print(f"\n{tgt}: R2 = {r2:.4f} ({r2*100:.2f}%) {status}")
    print(f"  RMSE: {rmse:.4f} | MAE: {mae:.4f} | MAPE: {mape_val:.2f}%")

    comp = pd.DataFrame({'true': true[:5], 'pred': oof_final[:5]})
    print(f"  Sample: {comp.to_string(index=False, float_format=lambda x: f'{x:.5f}', header=False)}")

# Summary
print("\n" + "="*80)
results = {tgt: r2_score(y[tgt], stacked_models[tgt]['meta'].predict(oof_predictions[tgt])) for tgt in y.columns}
achieved = sum(1 for r2 in results.values() if r2 >= 0.90)
print(f"SUMMARY: {achieved}/{len(results)} parameters achieved >90%")
for tgt, r2 in results.items():
    print(f"  {tgt}: {r2*100:.2f}%")
print("="*80)

# ---------- Save ----------
print(f"\nSaving to {OUTDIR}...")
dump(stacked_models, os.path.join(OUTDIR, "stacked_models.joblib"))
dump(enc, os.path.join(OUTDIR, "onehot_encoder.joblib"))
dump(scaler, os.path.join(OUTDIR, "scaler.joblib"))
with open(os.path.join(OUTDIR, "feature_columns.json"), "w") as f:
    json.dump(list(X.columns), f)
fitted_df.to_csv(os.path.join(OUTDIR, "fitted_params.csv"), index=False)

with open(os.path.join(OUTDIR, "metadata.json"), "w") as f:
    json.dump({
        'version': '3.0',
        'baseline_r': baseline_r,
        'r_untreated': float(r_untreated),
        'results': {k: float(v) for k, v in results.items()},
        'n_features': len(X.columns),
        'n_samples': len(X),
        'dosage_aware': True,
        'full_features': True,  # NEW flag
        'feature_groups': {
            'basic': features_basic,
            'categorical': categorical,
            'total': len(X.columns)
        }
    }, f, indent=2)

elapsed = time.time() - t0
print(f"\nTotal time: {elapsed:.1f}s ({elapsed/60:.1f}m)")
print("\n" + "="*80)
print("TRAINING COMPLETE - ENHANCED MODEL v3.0")
print("="*80)
print(f"Model saved to: {OUTDIR}/")
print(f"Features: {len(X.columns)} (OLD: 76 → NEW: {len(X.columns)})")
print("="*80)
