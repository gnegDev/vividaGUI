using System;

namespace vivida.Models;

public class Patient
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string PatientId { get; set; } = "";
    public DateTime CreatedAt { get; set; }

    // Обязательные поля
    public double Age { get; set; }
    public double TumorSizeBefore { get; set; }
    public double Kps { get; set; }
    public string Treatment { get; set; } = "";

    // Дозировки
    public double? DoseMgPerM2 { get; set; }
    public int? Cycles { get; set; }
    public double? TotalDoseGy { get; set; }
    public int? Fractions { get; set; }

    // Генетические маркеры
    public bool MgmtMethylation { get; set; }
    public bool IdhMutation { get; set; }
    public bool EgfrAmplification { get; set; }
    public bool TertMutation { get; set; }
    public bool AtrxMutation { get; set; }

    // Клинические признаки
    public double? EdemaVolume { get; set; }
    public double? SteroidDose { get; set; }
    public bool AntiseizureMeds { get; set; }

    // Неврологические симптомы
    public bool HasHeadache { get; set; }
    public bool HasSeizures { get; set; }
    public bool HasMotorDeficit { get; set; }
    public bool HasSensoryDeficit { get; set; }
    public bool HasCognitiveDecline { get; set; }
    public bool HasSpeechDisturbance { get; set; }
    public bool HasVisualDisturbance { get; set; }

    // Прочее
    public string? Gender { get; set; }
    public string? ResectionExtent { get; set; }
    public string? TumorLocation { get; set; }
    public string? ContrastEnhancement { get; set; }
    public string? Stage { get; set; }
    public string? Lateralization { get; set; }
    public string? RanoResponse { get; set; }
    public bool FamilyHistory { get; set; }
    public bool PreviousRadiation { get; set; }
}
