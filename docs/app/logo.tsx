import styles from "./logo.module.css";
import Image from "next/image";
import Link from "next/link";

export default function Logo() {
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH;
  return (
    <Link href="/" className="x:flex x:items-center">
      <Image src={`${basePath}/logo-light.svg`} alt="Suvereo" height={24} width={139} unoptimized className={`${styles.logo__image} ${styles["logo__image--light"]}`} />
      <Image src={`${basePath}/logo-dark.svg`} alt="Suvereo" height={24} width={139} unoptimized className={`${styles.logo__image} ${styles["logo__image--dark"]}`} />
    </Link>
  );
}
