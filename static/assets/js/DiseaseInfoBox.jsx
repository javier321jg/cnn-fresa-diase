import React, { useState, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

const DiseaseInfoBox = () => {
  const [diseaseInfo, setDiseaseInfo] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Function to fetch disease information from the Gemini API
  const fetchDiseaseInfo = async (diseaseName) => {
    const API_KEY = 'AIzaSyDjKdpyvvTSqACwLOAU0jPPgDZUKdLbLM4';
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=${API_KEY}`;
    
    const data = {
      contents: [{
        parts: [{
          text: `Proporciona información detallada sobre la enfermedad ${diseaseName} en fresas, incluyendo:
                1. Descripción de la enfermedad
                2. Causas principales
                3. Síntomas
                4. Recomendaciones de tratamiento
                
                Estructura la respuesta en secciones claras.`
        }]
      }],
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 1024
      }
    };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        throw new Error(`API response error: ${response.statusText}`);
      }

      const result = await response.json();
      return result.candidates[0].content.parts[0].text;
    } catch (error) {
      throw new Error(`Error fetching disease information: ${error.message}`);
    }
  };

  useEffect(() => {
    const loadDetectionsAndInfo = async () => {
      try {
        // Load detections from the detections.js file
        const response = await fetch('/static/assets/js/detections.js');
        const detectionsText = await response.text();
        const detections = JSON.parse(detectionsText.replace('const detections = ', '').replace(';', ''));
        
        const infoPromises = detections
          .filter(detection => detection.class !== 'hoja sana') // Exclude healthy leaves
          .map(async (detection) => {
            const info = await fetchDiseaseInfo(detection.class);
            return { [detection.class]: info };
          });

        const infoArray = await Promise.all(infoPromises);
        const infoObject = infoArray.reduce((acc, curr) => ({ ...acc, ...curr }), {});

        setDiseaseInfo(infoObject);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadDetectionsAndInfo();
  }, []);

  if (loading) {
    return <div className="p-4">Cargando información de enfermedades...</div>;
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(diseaseInfo).map(([disease, info]) => (
        <div key={disease} className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-2">{disease}</h3>
          <div className="whitespace-pre-wrap">{info}</div>
        </div>
      ))}
    </div>
  );
};

export default DiseaseInfoBox;
