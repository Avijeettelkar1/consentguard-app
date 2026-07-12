import { useInView } from '../hooks/useInView'
import ProductPreview from './ProductPreview'

export default function ProductSection() {
  const [ref, inView] = useInView(0.12)

  return (
    <section className="product-section">
      <div className="product-header">
        <span className="eyebrow">The report</span>
        <h2>One scan. The whole story.</h2>
        <p>
          Every undeclared tracker, its owner, the data it collects, your fine exposure, and a
          ready-to-file complaint — generated automatically and laid out like a legal exhibit.
        </p>
      </div>
      <div ref={ref} className={`reveal${inView ? ' in-view' : ''}`}>
        <ProductPreview />
      </div>
    </section>
  )
}
