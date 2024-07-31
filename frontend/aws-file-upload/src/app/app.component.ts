import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http'
import { S3Client } from '@aws-sdk/client-s3'
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'aws-file-upload';
  selectedFile: File | null = null;
  uploadProgress: number = 0;
  s3Client!: S3Client;
  apiBaseURL = environment.apiBaseURL

  constructor(private http: HttpClient) {
    this.s3Client = new S3Client({
      region: environment.AWS_CREDENTIAL.REGION,
      credentials: {
        accessKeyId: environment.AWS_CREDENTIAL.ACCESS_KEY,
        secretAccessKey: environment.AWS_CREDENTIAL.SECRET_KEY
      }
    })
  }

  onFileSelected(event: any) {
    this.selectedFile = event.target.files[0];
  }

  async onUpload() {
    if(this.selectedFile) {
      const CHUNK_SIZE = 5 * 1024 *1024;
      const file = this.selectedFile;
      const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

      // Step 1: Initialize mutlipart upload
      const uploadIdResponse = await this.http.post<{uploadId: string}>(`${this.apiBaseURL}create-multipart-upload`, {
        fileName: file.name
      }).toPromise()
      const uploadId = uploadIdResponse?.uploadId

      const uploadPromises = []

      // Step 2: Upload Parts
      for (let i=0; i< totalChunks; i++) {
        const start = i* CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, file.size);
        const chunk = file.slice(start, end);

        // Get presigned URL for the chunk
        const presignedUrlResponse = await this.http.post<{url: string}>(`${this.apiBaseURL}get-presigned-url`, {
          fileName : file.name,
          uploadId: uploadId,
          partNumber: i+1
        }).toPromise();

        const presignedUrl = presignedUrlResponse?.url ?? '';
        const uploadPromise = this.http.put(presignedUrl, chunk, {
          headers: {
            'Content-Type': 'application/octet-stream'
          },
          observe: 'events',
          reportProgress: true
        }).toPromise()

        uploadPromises.push(uploadPromise)
        
      }

      const uploadedParts = await Promise.all(uploadPromises)
     
      // Step 3: Complete multipart upload
      const parts = uploadedParts.map((response:any, index:any) => ({
        ETag: response.headers.get('ETag'),
        PartNumber: index+1
      }))

      await this.http.post(`${this.apiBaseURL}complete-multipart-upload`, {
        fileName: file.name,
        uploadId: uploadId,
        parts: parts
      }).toPromise()

      this.uploadProgress = 100;
    }
  }
}
