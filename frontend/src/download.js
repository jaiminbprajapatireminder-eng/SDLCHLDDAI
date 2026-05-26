import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'
import * as XLSX from 'xlsx'

export async function downloadPdf(element, filename) {
  if (!element) return
  const canvas = await html2canvas(element, {
    backgroundColor: '#0f172a',
    scale: 2,
    useCORS: true,
    logging: false,
  })
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF('p', 'mm', 'a4')
  const pdfWidth = pdf.internal.pageSize.getWidth()
  const pdfHeight = (canvas.height * pdfWidth) / canvas.width
  let heightLeft = pdfHeight
  let position = 0
  const pageHeight = pdf.internal.pageSize.getHeight()

  pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, pdfHeight)
  heightLeft -= pageHeight

  while (heightLeft > 0) {
    position = heightLeft - pdfHeight
    pdf.addPage()
    pdf.addImage(imgData, 'PNG', 0, position, pdfWidth, pdfHeight)
    heightLeft -= pageHeight
  }

  pdf.save(`${filename}.pdf`)
}

export function downloadExcel(headers, rows, filename) {
  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
  XLSX.writeFile(wb, `${filename}.xlsx`)
}

export function downloadTxt(content, filename) {
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${filename}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
