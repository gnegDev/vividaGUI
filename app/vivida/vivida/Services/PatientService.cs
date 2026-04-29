using vivida.Models;

namespace vivida.Services;

public class PatientService
{
    public OptimizeSummaryRequest BuildRequest(Patient p)
    {
        var req = new OptimizeSummaryRequest
        {
            Id = p.PatientId,
            Age = p.Age,
            TumorSizeBefore = p.TumorSizeBefore,
            Kps = p.Kps,
            Treatment = p.Treatment,
            MgmtMethylation = p.MgmtMethylation,
            IdhMutation = p.IdhMutation,
            EgfrAmplification = p.EgfrAmplification,
            TertMutation = p.TertMutation,
            AtrxMutation = p.AtrxMutation,
            AntiseizureMeds = p.AntiseizureMeds,
            HasHeadache = p.HasHeadache,
            HasSeizures = p.HasSeizures,
            HasMotorDeficit = p.HasMotorDeficit,
            HasSensoryDeficit = p.HasSensoryDeficit,
            HasCognitiveDecline = p.HasCognitiveDecline,
            HasSpeechDisturbance = p.HasSpeechDisturbance,
            HasVisualDisturbance = p.HasVisualDisturbance,
            ContrastEnhancement = p.ContrastEnhancement,
            FamilyHistory = p.FamilyHistory,
            PreviousRadiation = p.PreviousRadiation,
            EdemaVolume = p.EdemaVolume,
            SteroidDose = p.SteroidDose,
            Gender = string.IsNullOrEmpty(p.Gender) ? null : p.Gender,
            ResectionExtent = string.IsNullOrEmpty(p.ResectionExtent) ? null : p.ResectionExtent,
            TumorLocation = string.IsNullOrWhiteSpace(p.TumorLocation) ? null : p.TumorLocation,
            Stage = string.IsNullOrWhiteSpace(p.Stage) ? null : p.Stage,
            Lateralization = string.IsNullOrEmpty(p.Lateralization) ? null : p.Lateralization,
            RanoResponse = string.IsNullOrWhiteSpace(p.RanoResponse) ? null : p.RanoResponse,
        };

        if (p.DoseMgPerM2.HasValue || p.Cycles.HasValue)
            req.Chemotherapy = new ChemotherapyRequest
            {
                Drug = "Temozolomide",
                DoseMgPerM2 = p.DoseMgPerM2,
                Cycles = p.Cycles
            };

        if (p.TotalDoseGy.HasValue || p.Fractions.HasValue)
            req.Radiotherapy = new RadiotherapyRequest
            {
                TotalDoseGy = p.TotalDoseGy,
                Fractions = p.Fractions
            };

        return req;
    }
}
