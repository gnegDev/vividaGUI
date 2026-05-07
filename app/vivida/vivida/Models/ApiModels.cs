using System.Text.Json.Serialization;

namespace vivida.Models;

public class ChemotherapyRequest
{
    [JsonPropertyName("drug")]
    public string Drug { get; set; } = "Temozolomide";

    [JsonPropertyName("dose_mg_per_m2")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public double? DoseMgPerM2 { get; set; }

    [JsonPropertyName("cycles")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Cycles { get; set; }
}

public class RadiotherapyRequest
{
    [JsonPropertyName("total_dose_Gy")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public double? TotalDoseGy { get; set; }

    [JsonPropertyName("fractions")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public int? Fractions { get; set; }
}

public class OptimizeSummaryRequest
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("age")]
    public double Age { get; set; }

    [JsonPropertyName("tumor_size_before")]
    public double TumorSizeBefore { get; set; }

    [JsonPropertyName("kps")]
    public double Kps { get; set; }

    [JsonPropertyName("treatment")]
    public string Treatment { get; set; } = "";

    [JsonPropertyName("chemotherapy")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public ChemotherapyRequest? Chemotherapy { get; set; }

    [JsonPropertyName("radiotherapy")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public RadiotherapyRequest? Radiotherapy { get; set; }

    [JsonPropertyName("mgmt_methylation")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool MgmtMethylation { get; set; }

    [JsonPropertyName("idh_mutation")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool IdhMutation { get; set; }

    [JsonPropertyName("egfr_amplification")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool EgfrAmplification { get; set; }

    [JsonPropertyName("tert_mutation")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool TertMutation { get; set; }

    [JsonPropertyName("atrx_mutation")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool AtrxMutation { get; set; }

    [JsonPropertyName("edema_volume")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public double? EdemaVolume { get; set; }

    [JsonPropertyName("steroid_dose")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public double? SteroidDose { get; set; }

    [JsonPropertyName("antiseizure_meds")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool AntiseizureMeds { get; set; }

    [JsonPropertyName("has_headache")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasHeadache { get; set; }

    [JsonPropertyName("has_seizures")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasSeizures { get; set; }

    [JsonPropertyName("has_motor_deficit")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasMotorDeficit { get; set; }

    [JsonPropertyName("has_sensory_deficit")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasSensoryDeficit { get; set; }

    [JsonPropertyName("has_cognitive_decline")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasCognitiveDecline { get; set; }

    [JsonPropertyName("has_speech_disturbance")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasSpeechDisturbance { get; set; }

    [JsonPropertyName("has_visual_disturbance")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool HasVisualDisturbance { get; set; }

    [JsonPropertyName("gender")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Gender { get; set; }

    [JsonPropertyName("resection_extent")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? ResectionExtent { get; set; }

    [JsonPropertyName("tumor_location")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? TumorLocation { get; set; }

    [JsonPropertyName("contrast_enhancement")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool ContrastEnhancement { get; set; }

    [JsonPropertyName("stage")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Stage { get; set; }

    [JsonPropertyName("lateralization")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Lateralization { get; set; }

    [JsonPropertyName("rano_response")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? RanoResponse { get; set; }

    [JsonPropertyName("family_history")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool FamilyHistory { get; set; }

    [JsonPropertyName("previous_radiation")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingDefault)]
    public bool PreviousRadiation { get; set; }
}

// Модели ответа

public class DoctorPlan
{
    [JsonPropertyName("treatment_type")]
    public string TreatmentType { get; set; } = "";

    [JsonPropertyName("prediction")]
    public double Prediction { get; set; }
}

public class ChemotherapyResult
{
    [JsonPropertyName("dose_mg_per_m2")]
    public double? DoseMgPerM2 { get; set; }
}

public class RadiotherapyResult
{
    [JsonPropertyName("total_dose_Gy")]
    public double? TotalDoseGy { get; set; }

    [JsonPropertyName("fractions")]
    public int? Fractions { get; set; }

    [JsonPropertyName("BED")]
    public double? Bed { get; set; }
}

public class GlobalOptimal
{
    [JsonPropertyName("treatment_type")]
    public string TreatmentType { get; set; } = "";

    [JsonPropertyName("prediction")]
    public double Prediction { get; set; }

    [JsonPropertyName("improvement_percent")]
    public double ImprovementPercent { get; set; }

    [JsonPropertyName("chemotherapy")]
    public ChemotherapyResult? Chemotherapy { get; set; }

    [JsonPropertyName("radiotherapy")]
    public RadiotherapyResult? Radiotherapy { get; set; }
}

public class LocalOptimal
{
    [JsonPropertyName("treatment_type")]
    public string TreatmentType { get; set; } = "";

    [JsonPropertyName("prediction")]
    public double Prediction { get; set; }

    [JsonPropertyName("improvement_percent")]
    public double ImprovementPercent { get; set; }
}

public class OptimizeSummaryResponse
{
    [JsonPropertyName("model_version")]
    public string ModelVersion { get; set; } = "";

    [JsonPropertyName("patient_id")]
    public string PatientId { get; set; } = "";

    [JsonPropertyName("doctor_plan")]
    public DoctorPlan? DoctorPlan { get; set; }

    [JsonPropertyName("global_optimal")]
    public GlobalOptimal? GlobalOptimal { get; set; }

    [JsonPropertyName("local_optimal")]
    public LocalOptimal? LocalOptimal { get; set; }

    [JsonPropertyName("recommendation")]
    public string Recommendation { get; set; } = "";
}
