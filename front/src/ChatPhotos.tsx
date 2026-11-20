import { X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { readChatPhoto, type ChatPhoto } from './photoStore'

export function DraftPhoto({ file, onRemove, onInvalid, disabled }: {
  file: File
  onRemove: () => void
  onInvalid: () => void
  disabled: boolean
}) {
  const [preview, setPreview] = useState<{ file: File; url: string }>()

  useEffect(() => {
    const url = URL.createObjectURL(file)
    setPreview({ file, url })
    return () => URL.revokeObjectURL(url)
  }, [file])

  return (
    <div className="draft-photo">
      {preview?.file === file && <img src={preview.url} alt="" onError={onInvalid} />}
      <span title={file.name}>{file.name}</span>
      <button type="button" className="icon-button" aria-label="Убрать фото" disabled={disabled} onClick={onRemove}>
        <X size={17} />
      </button>
    </div>
  )
}

export function MessagePhoto({ photo, userId }: { photo: ChatPhoto; userId: string }) {
  const [url, setUrl] = useState('')
  const [unavailable, setUnavailable] = useState(false)

  useEffect(() => {
    let active = true
    let objectUrl = ''
    void readChatPhoto(userId, photo.id).then((blob) => {
      if (!active) return
      if (blob) {
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      } else {
        setUnavailable(true)
      }
    }, () => { if (active) setUnavailable(true) })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [photo.id, userId])

  if (unavailable) return <p className="muted">Фото недоступно в этом браузере.</p>
  if (!url) return null
  return <img className="message-photo" src={url} alt={photo.name} onError={() => setUnavailable(true)} />
}
