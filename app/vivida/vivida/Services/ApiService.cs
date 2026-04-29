using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using vivida.Models;

namespace vivida.Services;

public class ApiService
{
    private readonly HttpClient _http;
    private const string BaseUrl = "http://localhost:8080";

    public ApiService()
    {
        _http = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
    }

    public async Task<string> GetHealthAsync()
    {
        var response = await _http.GetAsync($"{BaseUrl}/health");
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadAsStringAsync();
    }

    public async Task<(OptimizeSummaryResponse response, string rawJson)> OptimizeSummaryAsync(OptimizeSummaryRequest request)
    {
        var httpResponse = await _http.PostAsJsonAsync($"{BaseUrl}/optimize/summary", request);
        var rawJson = await httpResponse.Content.ReadAsStringAsync();

        if (!httpResponse.IsSuccessStatusCode)
            throw new HttpRequestException($"Сервер вернул {(int)httpResponse.StatusCode}: {rawJson}");

        var result = await httpResponse.Content.ReadFromJsonAsync<OptimizeSummaryResponse>()
            ?? throw new Exception("Не удалось разобрать ответ сервера");

        return (result, rawJson);
    }
}
