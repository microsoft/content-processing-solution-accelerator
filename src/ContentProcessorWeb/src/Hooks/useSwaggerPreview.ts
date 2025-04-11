// src/hooks/useSwaggerPreview.ts
import { toast } from 'react-toastify';

const useSwaggerPreview = () => {
  const openSwaggerUI = (swaggerJSON: object | null, apiUrl: string, token?: string) => {
    if (!swaggerJSON) {
      toast.error('Swagger JSON is missing!');
      return;
    }

    // Clone the Swagger JSON to avoid mutation
    const swaggerSpec = structuredClone(swaggerJSON) as any;
    swaggerSpec.servers = [{ url: apiUrl, description: 'API Endpoint' }];

    const newWindow = window.open('', '_blank');
    if (!newWindow) return;

    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Swagger UI</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
      </head>
      <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
        <script>
          window.onload = function () {
            const spec = ${JSON.stringify(swaggerSpec)};
            const token = "${token ?? ''}";

            SwaggerUIBundle({
              spec: spec,
              dom_id: '#swagger-ui',
              requestInterceptor: function (req) {
                if (token) {
                  req.headers['Authorization'] = 'Bearer ' + token;
                }
                return req;
              }
            });
          };
        </script>
      </body>
      </html>
    `;

    newWindow.document.write(htmlContent);
    newWindow.document.close();
  };

  return { openSwaggerUI };
};

export default useSwaggerPreview;
