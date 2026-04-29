using System;

namespace vivida.Models;

public class AnalysisResult
{
    public int Id { get; set; }
    public int PatientDbId { get; set; }
    public DateTime CreatedAt { get; set; }
    public string ResultJson { get; set; } = "";

    public Patient? Patient { get; set; }
}
